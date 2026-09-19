import asyncio
import logging
import os
import socket
from contextlib import suppress
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, update

from app.config.runtime import runtime_settings
from app.db.database import SessionLocal, engine
from app.db.repository import generations
from app.llm import LLMError, LLMGateway
from app.llm.retry_policy import retry_delay
from app.memory.context_builder import build_context
from app.memory.history import load_history
from app.memory.summary import prepare_memory
from app.models import GenerationRequest, utc_now
from app.models.generation_request import TERMINAL_GENERATION_STATUSES
from app.queue.events import publish_event
from app.queue.manager import JOBS_STREAM, WORKER_GROUP, QueueManager
from app.rate_limit.conversation_lock import ConversationBusy, conversation_lock
from app.redis_client import close_redis_clients, get_blocking_redis, get_redis
from app.routing.fallback import fallback_model
from app.routing.model_router import route_model
from app.services.generation import fail_request, finalize_success

logger = logging.getLogger(__name__)


async def _heartbeat_generation(request_id: UUID, lease_seconds: int) -> None:
    while True:
        await asyncio.sleep(lease_seconds / 3)
        try:
            async with SessionLocal() as session:
                await session.execute(
                    update(GenerationRequest)
                    .where(
                        GenerationRequest.id == request_id,
                        GenerationRequest.status == "GENERATING",
                    )
                    .values(updated_at=utc_now())
                )
                await session.commit()
        except Exception:
            logger.warning(
                "generation_heartbeat_failed", extra={"request_id": str(request_id)}
            )


async def _set_retrying(
    request_id: UUID, error: LLMError, next_model: str, delay: float
) -> None:
    settings = await runtime_settings()
    # Commit trạng thái trước khi đưa delayed queue để recovery có thể nhặt lại.
    async with SessionLocal() as session:
        request = await session.get(GenerationRequest, request_id, with_for_update=True)
        if not request or request.status in TERMINAL_GENERATION_STATUSES:
            return
        request.status = "RETRYING"
        request.actual_model = next_model
        request.error_code = error.code
        request.error_message = error.public_message
        request.updated_at = utc_now()
        await session.commit()
    await QueueManager().delay(request_id, delay)
    await publish_event(
        request_id,
        "retrying",
        {"status": "RETRYING", "retry_after": round(delay, 2)},
        settings.queue_event_ttl_seconds,
    )


async def process_job(message_id: str, request_id: UUID) -> None:
    queue = QueueManager()
    settings = await runtime_settings()
    async with SessionLocal() as session:
        request = await generations.claim(session, request_id)
        if not request:
            await session.rollback()
            existing = await generations.get_by_id(session, request_id)
            if not existing or existing.status in TERMINAL_GENERATION_STATUSES:
                await queue.ack(message_id)
                if existing:
                    await queue.complete(request_id)
            return
        await session.commit()

    if utc_now() - request.created_at > timedelta(seconds=settings.max_queue_wait_seconds):
        async with SessionLocal() as session:
            await fail_request(
                session, request_id, "PROVIDER_UNAVAILABLE", "Yêu cầu chờ quá thời gian cho phép"
            )
        await publish_event(
            request_id,
            "failed",
            {
                "status": "FAILED",
                "error_code": "PROVIDER_UNAVAILABLE",
                "message": "Yêu cầu chờ quá thời gian cho phép",
            },
            settings.queue_event_ttl_seconds,
        )
        await queue.ack(message_id)
        await queue.complete(request_id)
        return

    gateway = LLMGateway(request_id, settings.exact_token_count_threshold)
    logger.info(
        "generation_started",
        extra={
            "request_id": str(request_id),
            "user_id": str(request.user_id),
            "conversation_id": str(request.conversation_id),
            "operation": request.operation,
            "status": request.status,
        },
    )
    heartbeat = asyncio.create_task(
        _heartbeat_generation(request_id, settings.worker_lease_seconds)
    )
    try:
        async with conversation_lock(request.conversation_id, settings):
            await publish_event(
                request_id,
                "generating",
                {"status": "GENERATING", "attempt": request.attempt_count},
                settings.queue_event_ttl_seconds,
            )
            async with SessionLocal() as session:
                history = await load_history(session, request.conversation_id)
                memory = await prepare_memory(
                    session,
                    request.conversation_id,
                    history,
                    request.question,
                    gateway,
                    settings,
                )
            context = build_context(memory.summary, memory.recent_messages, request.question)

            async def on_delta(text: str) -> None:
                await publish_event(
                    request_id,
                    "delta",
                    {"text": text},
                    settings.queue_event_ttl_seconds,
                )

            current_model = request.actual_model or route_model(
                "chat", request.requested_model, settings
            )
            result = await gateway.generate_once(
                context,
                requested_model=request.requested_model,
                model_override=current_model,
                on_delta=on_delta,
            )
            async with SessionLocal() as session:
                pair = await finalize_success(session, request_id, result.text, result.model)
            if pair:
                await publish_event(
                    request_id,
                    "completed",
                    {
                        "status": "DONE",
                        "user_message_id": str(pair[0].id),
                        "assistant_message_id": str(pair[1].id),
                    },
                    settings.queue_event_ttl_seconds,
                )
            await queue.ack(message_id)
            await queue.complete(request_id)
    except ConversationBusy:
        error = LLMError("CONVERSATION_BUSY", "Hội thoại đang được xử lý", retryable=True)
        next_model = request.actual_model or route_model(
            "chat", request.requested_model, settings
        )
        if request.attempt_count < settings.queue_job_max_attempts:
            await _set_retrying(request_id, error, next_model, 1)
        else:
            async with SessionLocal() as session:
                await fail_request(session, request_id, error.code, error.public_message)
            await publish_event(
                request_id,
                "failed",
                {
                    "status": "FAILED",
                    "error_code": error.code,
                    "message": error.public_message,
                },
                settings.queue_event_ttl_seconds,
            )
            await queue.complete(request_id)
        await queue.ack(message_id)
    except LLMError as error:
        current_model = request.actual_model or route_model(
            "chat", request.requested_model, settings
        )
        fallback = (
            fallback_model(current_model, "chat", settings)
            if error.retryable and not error.had_delta
            else None
        )
        delay = retry_delay(error, request.attempt_count, settings)
        retry_elapsed = (
            utc_now() - (request.started_at or request.created_at)
        ).total_seconds()
        can_retry = (
            error.retryable
            and not error.had_delta
            and retry_elapsed + delay < settings.gemini_max_retry_elapsed_seconds
            and request.attempt_count < min(
                settings.queue_job_max_attempts, settings.gemini_max_retry_attempts
            )
        )
        if can_retry:
            await _set_retrying(request_id, error, fallback or current_model, delay)
        else:
            async with SessionLocal() as session:
                await fail_request(session, request_id, error.code, error.public_message)
            await publish_event(
                request_id,
                "failed",
                {"status": "FAILED", "error_code": error.code, "message": error.public_message},
                settings.queue_event_ttl_seconds,
            )
            await queue.complete(request_id)
        await queue.ack(message_id)
    finally:
        heartbeat.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat


async def _recover_stuck() -> None:
    settings = await runtime_settings()
    cutoff = utc_now() - timedelta(seconds=settings.worker_lease_seconds * 2)
    recovered_at = utc_now()
    async with SessionLocal() as session:
        # Heartbeat worker cập nhật updated_at; chỉ generation thực sự mất worker mới bị thu hồi.
        stuck_ids = list((await session.scalars(
            update(GenerationRequest)
            .where(
                GenerationRequest.status == "GENERATING",
                GenerationRequest.updated_at < cutoff,
            )
            .values(status="RETRYING", updated_at=recovered_at)
            .returning(GenerationRequest.id)
        )).all())
        stale_ids = list(
            await session.scalars(
                select(GenerationRequest.id).where(
                    GenerationRequest.status.in_(("PENDING", "RETRYING")),
                    GenerationRequest.updated_at < cutoff,
                )
            )
        )
        request_ids = [*stuck_ids, *stale_ids]
        if request_ids:
            # Tạo recovery lease trong PostgreSQL để scheduler không bơm trùng mỗi giây.
            await session.execute(
                update(GenerationRequest)
                .where(GenerationRequest.id.in_(request_ids))
                .values(updated_at=recovered_at)
            )
        await session.commit()
    for request_id in request_ids:
        try:
            await QueueManager().recover(request_id, settings.max_queue_size)
        except Exception:
            break


async def scheduler() -> None:
    queue = QueueManager()
    while True:
        settings = await runtime_settings()
        await queue.promote_due(settings.max_queue_size)
        await _recover_stuck()
        await asyncio.sleep(1)


async def worker() -> None:
    queue = QueueManager()
    await queue.ensure_group()
    # PID có thể trùng giữa các container; hostname giữ consumer Redis duy nhất
    # khi worker được scale ngang bằng Docker Compose.
    consumer = f"worker-{socket.gethostname()}-{os.getpid()}"
    semaphore = asyncio.Semaphore((await runtime_settings()).worker_concurrency)

    async def run(message_id: str, request_id: str) -> None:
        async with semaphore:
            try:
                await process_job(message_id, UUID(request_id))
            except Exception:
                # Không ACK: XAUTOCLAIM/recovery sẽ giao lại job sau lease.
                logger.exception("worker_job_failed", extra={"request_id": request_id})

    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(scheduler())
        while True:
            # Luôn kiểm tra pending cũ; nếu chỉ làm khi queue rỗng thì traffic liên
            # tục có thể khiến job của worker đã chết không bao giờ được claim lại.
            claimed = await get_redis().xautoclaim(
                JOBS_STREAM,
                WORKER_GROUP,
                consumer,
                min_idle_time=(await runtime_settings()).worker_lease_seconds * 1000,
                start_id="0-0",
                count=20,
            )
            messages = claimed[1] if len(claimed) > 1 else []
            rows = [(JOBS_STREAM, messages)] if messages else await get_blocking_redis().xreadgroup(
                WORKER_GROUP,
                consumer,
                {JOBS_STREAM: ">"},
                count=20,
                block=5000,
            )
            for _, messages in rows:
                for message_id, fields in messages:
                    tasks.create_task(run(str(message_id), fields["request_id"]))


async def main() -> None:
    try:
        await worker()
    finally:
        await close_redis_clients()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
