import asyncio
import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.runtime import runtime_settings
from app.db.repository import conversations
from app.llm import LLMError, LLMGateway
from app.llm.retry_policy import retry_delay
from app.memory.context_builder import build_context
from app.memory.history import load_history
from app.memory.summary import prepare_memory
from app.models import Conversation, GenerationRequest, Message, utc_now
from app.rate_limit.conversation_lock import conversation_lock
from app.rate_limit.user_limiter import UserLimiter
from app.routing.fallback import fallback_model
from app.routing.model_router import route_model
from app.services import generation as generation_service


class UserRateLimited(RuntimeError):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after


async def create_conversation(session: AsyncSession, user_id: UUID) -> Conversation:
    conversation = await conversations.create(session, user_id)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def list_conversations(session: AsyncSession, user_id: UUID) -> list[Conversation]:
    return await conversations.list_by_user(session, user_id)


async def get_conversation(
    session: AsyncSession, conversation_id: UUID, user_id: UUID
) -> Conversation | None:
    return await conversations.get_owned(
        session, conversation_id, user_id, with_messages=True
    )


async def chat(
    session: AsyncSession, conversation_id: UUID, user_id: UUID, question: str
) -> tuple[str, Message, Message] | None:
    settings = await runtime_settings()
    if not settings.legacy_sync_chat_enabled:
        raise LLMError("INTERNAL_ERROR", "Luồng chat đồng bộ đang tắt")

    limit = await UserLimiter().consume(user_id, settings)
    if not limit.allowed:
        raise UserRateLimited(limit.retry_after_seconds)

    request = await generation_service.create_sync_request(
        session, user_id, conversation_id, question, settings
    )
    if not request:
        return None

    gateway = LLMGateway(request.id)
    try:
        async with conversation_lock(conversation_id, settings):
            request.status = "GENERATING"
            request.started_at = utc_now()
            await session.commit()

            history = await load_history(session, conversation_id)
            memory_attempt = 0
            memory_started = time.monotonic()
            while True:
                memory_attempt += 1
                try:
                    memory = await prepare_memory(
                        session, conversation_id, history, question, gateway
                    )
                    break
                except LLMError as error:
                    delay = retry_delay(error, memory_attempt, settings)
                    elapsed = time.monotonic() - memory_started
                    if (
                        not error.retryable
                        or memory_attempt >= settings.gemini_max_retry_attempts
                        or elapsed + delay >= settings.gemini_max_retry_elapsed_seconds
                    ):
                        raise
                    await asyncio.sleep(delay)
            context = build_context(memory.summary, memory.recent_messages, question)

            started = time.monotonic()
            attempt = 0
            model = route_model("chat", request.requested_model, settings)
            while True:
                attempt += 1
                current = await session.get(GenerationRequest, request.id)
                if current:
                    current.attempt_count = attempt
                    current.actual_model = model
                    current.updated_at = utc_now()
                    await session.commit()
                try:
                    result = await gateway.generate_once(
                        context, requested_model=request.requested_model, model_override=model
                    )
                    break
                except LLMError as error:
                    elapsed = time.monotonic() - started
                    delay = retry_delay(error, attempt, settings)
                    fallback = fallback_model(model, "chat", settings)
                    if (
                        not error.retryable
                        or attempt >= settings.gemini_max_retry_attempts
                        or elapsed + delay >= settings.gemini_max_retry_elapsed_seconds
                    ):
                        raise
                    if fallback:
                        model = fallback
                    await asyncio.sleep(delay)

            pair = await generation_service.finalize_success(
                session, request.id, result.text, result.model
            )
            if not pair:
                raise LLMError("CANCELLED", "Yêu cầu đã bị hủy")
            return result.text, pair[0], pair[1]
    except Exception as exc:
        error = exc if isinstance(exc, LLMError) else LLMError(
            "INTERNAL_ERROR", "Không thể xử lý yêu cầu"
        )
        await generation_service.fail_request(
            session, request.id, error.code, error.public_message
        )
        raise
