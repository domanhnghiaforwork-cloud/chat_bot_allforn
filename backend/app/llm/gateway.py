import time
import logging
from collections.abc import Awaitable, Callable
from uuid import UUID

from google.genai import types
from sqlalchemy import func, select

from app.config.prompts import SUMMARY_PROMPT
from app.config.runtime import runtime_settings
from app.config.settings import get_settings
from app.db.database import SessionLocal
from app.llm.client import gemini_client
from app.llm.errors import LLMError, normalize_provider_error
from app.llm.generation import GenerationResult, estimate_tokens, should_count_exactly
from app.memory.context_builder import ChatContext, messages_to_contents
from app.models import GenerationRequest, Message, ModelUsage
from app.rate_limit.model_limiter import ModelLimiter
from app.routing.circuit_breaker import ensure_circuit_closed, record_failure, record_success
from app.routing.fallback import fallback_model
from app.routing.model_router import route_model


DeltaCallback = Callable[[str], Awaitable[None]]
logger = logging.getLogger(__name__)


def _messages_text(messages: list[Message]) -> str:
    return "\n".join(f"{message.role}: {message.content}" for message in messages)


def _context_text(context: ChatContext) -> str:
    return context.system_instruction + "\n" + "\n".join(
        part.text or "" for content in context.contents for part in (content.parts or [])
    )


async def _provider_count_tokens(
    client, model: str, contents, system_instruction: str | None = None
) -> int:
    counted_contents = contents
    if system_instruction:
        items = contents if isinstance(contents, list) else [contents]
        counted_contents = [
            types.Content(
                role="user", parts=[types.Part.from_text(text=system_instruction)]
            ),
            *items,
        ]
    response = await client.models.count_tokens(model=model, contents=counted_contents)
    return response.total_tokens or 0


class LLMGateway:
    def __init__(self, request_id: UUID, exact_count_threshold: float | None = None):
        self.request_id = request_id
        self.model_limiter = ModelLimiter()
        self.exact_count_threshold = (
            exact_count_threshold
            if exact_count_threshold is not None
            else get_settings().exact_token_count_threshold
        )

    async def _write_usage(
        self,
        *,
        operation: str,
        model: str,
        estimated: int,
        actual_input: int | None,
        output: int | None,
        status_code: int | None,
        status: str,
        latency_ms: int,
        error_code: str | None,
    ) -> None:
        async with SessionLocal() as session:
            # Khóa request để attempt_number tăng đơn điệu qua cả retry/worker restart.
            request = await session.scalar(
                select(GenerationRequest)
                .where(GenerationRequest.id == self.request_id)
                .with_for_update()
            )
            if not request:
                raise RuntimeError("Generation request không còn tồn tại")
            attempt_number = int(
                await session.scalar(
                    select(func.coalesce(func.max(ModelUsage.attempt_number), 0)).where(
                        ModelUsage.generation_request_id == self.request_id
                    )
                )
                or 0
            ) + 1
            session.add(
                ModelUsage(
                    generation_request_id=self.request_id,
                    operation=operation,
                    model=model,
                    attempt_number=attempt_number,
                    estimated_input_tokens=estimated,
                    actual_input_tokens=actual_input,
                    output_tokens=output,
                    provider_status_code=status_code,
                    status=status,
                    latency_ms=latency_ms,
                    error_code=error_code,
                )
            )
            await session.commit()
        logger.info(
            "llm_attempt",
            extra={
                "request_id": str(self.request_id),
                "user_id": str(request.user_id),
                "conversation_id": str(request.conversation_id),
                "operation": operation,
                "model": model,
                "attempt": attempt_number,
                "status": status,
                "latency_ms": latency_ms,
                "error_code": error_code,
            },
        )

    async def _count(self, contents, system_instruction: str | None, operation: str) -> int:
        settings = await runtime_settings()
        model = route_model(operation, None, settings)
        estimated = estimate_tokens(f"{system_instruction or ''}\n{contents}")
        if not await ensure_circuit_closed(settings.gemini_quota_project_id, model):
            raise LLMError("PROVIDER_UNAVAILABLE", "Circuit model đang mở", retryable=True)
        reservation = await self.model_limiter.reserve(settings, model, estimated)
        if not reservation.allowed:
            raise LLMError(
                "PROVIDER_RATE_LIMITED", "Quota model chưa sẵn sàng", retryable=True,
                retry_after_seconds=60,
            )
        started = time.perf_counter()
        try:
            async with gemini_client(settings) as client:
                total = await _provider_count_tokens(
                    client, model, contents, system_instruction
                )
        except Exception as exc:
            error = normalize_provider_error(exc)
            if error.retryable:
                try:
                    await record_failure(settings.gemini_quota_project_id, model)
                except Exception:
                    logger.warning("circuit_update_failed", extra={"model": model})
            await self._write_usage(
                operation="count_tokens", model=model, estimated=estimated, actual_input=None,
                output=None, status_code=error.provider_status_code, status="ERROR",
                latency_ms=int((time.perf_counter() - started) * 1000), error_code=error.code,
            )
            raise error from exc
        try:
            await self.model_limiter.reconcile(reservation, total)
            await record_success(settings.gemini_quota_project_id, model)
        except Exception:
            # Provider đã trả kết quả; lỗi housekeeping không được gây gọi lặp.
            logger.warning("quota_reconcile_failed", extra={"model": model})
        await self._write_usage(
            operation="count_tokens", model=model, estimated=estimated, actual_input=total,
            output=0, status_code=200, status="SUCCESS",
            latency_ms=int((time.perf_counter() - started) * 1000), error_code=None,
        )
        return total

    async def count_text_tokens(self, text: str, operation: str = "chat") -> int:
        return await self._count(text, None, operation) if text else 0

    async def count_message_tokens(self, messages: list[Message]) -> int:
        return await self._count(messages_to_contents(messages), None, "chat") if messages else 0

    async def count_context_tokens(self, context: ChatContext) -> int:
        return await self._count(context.contents, context.system_instruction, "chat")

    async def measure_text_tokens(
        self, text: str, limit: int, operation: str = "chat"
    ) -> int:
        if not text:
            return 0
        estimated = estimate_tokens(text)
        if should_count_exactly(estimated, limit, self.exact_count_threshold):
            return await self.count_text_tokens(text, operation)
        return estimated

    async def measure_message_tokens(self, messages: list[Message], limit: int) -> int:
        if not messages:
            return 0
        estimated = estimate_tokens(_messages_text(messages))
        if should_count_exactly(estimated, limit, self.exact_count_threshold):
            return await self.count_message_tokens(messages)
        return estimated

    async def measure_context_tokens(self, context: ChatContext, limit: int) -> int:
        estimated = estimate_tokens(_context_text(context))
        if should_count_exactly(estimated, limit, self.exact_count_threshold):
            return await self.count_context_tokens(context)
        return estimated

    async def generate_once(
        self,
        context: ChatContext,
        *,
        operation: str = "chat",
        requested_model: str | None = None,
        model_override: str | None = None,
        on_delta: DeltaCallback | None = None,
    ) -> GenerationResult:
        settings = await runtime_settings()
        model = model_override or route_model(operation, requested_model, settings)
        estimated = estimate_tokens(_context_text(context))
        if not await ensure_circuit_closed(settings.gemini_quota_project_id, model):
            raise LLMError("PROVIDER_UNAVAILABLE", "Circuit model đang mở", retryable=True)
        reservation = await self.model_limiter.reserve(settings, model, estimated)
        if not reservation.allowed:
            raise LLMError(
                "PROVIDER_RATE_LIMITED", "Quota model chưa sẵn sàng", retryable=True,
                retry_after_seconds=60,
            )

        started = time.perf_counter()
        had_delta = False
        try:
            config = types.GenerateContentConfig(
                system_instruction=context.system_instruction,
                max_output_tokens=(
                    settings.max_history_summary_tokens
                    if operation == "summary"
                    else settings.max_chat_output_tokens
                ),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            )
            async with gemini_client(settings) as client:
                if on_delta:
                    pieces: list[str] = []
                    final_usage = None
                    stream = await client.models.generate_content_stream(
                        model=model, contents=context.contents, config=config
                    )
                    async for chunk in stream:
                        final_usage = chunk.usage_metadata or final_usage
                        if chunk.text:
                            had_delta = True
                            pieces.append(chunk.text)
                            await on_delta(chunk.text)
                    text = "".join(pieces)
                    usage = final_usage
                else:
                    response = await client.models.generate_content(
                        model=model, contents=context.contents, config=config
                    )
                    text = response.text or ""
                    usage = response.usage_metadata
            if not text:
                raise LLMError("SAFETY_BLOCKED", "Gemini không trả về nội dung")
            actual_input = int(usage.prompt_token_count or estimated) if usage else estimated
            output = int(usage.candidates_token_count or 0) if usage else 0
        except Exception as exc:
            error = normalize_provider_error(exc, had_delta=had_delta)
            if error.retryable:
                try:
                    await record_failure(settings.gemini_quota_project_id, model)
                except Exception:
                    logger.warning("circuit_update_failed", extra={"model": model})
            await self._write_usage(
                operation=operation, model=model, estimated=estimated,
                actual_input=None, output=None, status_code=error.provider_status_code,
                status="ERROR", latency_ms=int((time.perf_counter() - started) * 1000),
                error_code=error.code,
            )
            raise error from exc
        try:
            await self.model_limiter.reconcile(reservation, actual_input)
            await record_success(settings.gemini_quota_project_id, model)
        except Exception:
            logger.warning("quota_reconcile_failed", extra={"model": model})
        await self._write_usage(
            operation=operation, model=model, estimated=estimated,
            actual_input=actual_input, output=output, status_code=200, status="SUCCESS",
            latency_ms=int((time.perf_counter() - started) * 1000), error_code=None,
        )
        return GenerationResult(text, model, actual_input, output)

    async def generate_summary(self, previous: str, messages: list[Message]) -> str:
        settings = await runtime_settings()
        summary = previous
        pending = messages.copy()
        first_run = True
        while pending or first_run:
            first_run = False
            # Chỉ cắt tại biên lượt hoàn chỉnh user-assistant.
            sizes = [
                index
                for index in range(1, len(pending) + 1)
                if index == len(pending)
                or not (
                    pending[index - 1].role == "user"
                    and pending[index].role == "assistant"
                )
            ]

            def prompt_for(count: int) -> str:
                transcript = "\n".join(
                    f"{item.role}: {item.content}" for item in pending[:count]
                )
                return (
                    f"Bản tóm tắt mới không vượt quá {settings.max_history_summary_tokens} token."
                    f"\n\nBản tóm tắt hiện tại:\n{summary or '(chưa có)'}"
                    f"\n\nĐoạn hội thoại mới:\n{transcript or '(không có)'}"
                )

            take = 0
            prompt = prompt_for(0)
            if sizes:
                left, right = 0, len(sizes) - 1
                while left <= right:
                    middle = (left + right) // 2
                    candidate_take = sizes[middle]
                    candidate = prompt_for(candidate_take)
                    if await self.measure_text_tokens(
                        candidate, settings.max_summary_input_tokens, "summary"
                    ) <= settings.max_summary_input_tokens:
                        take, prompt = candidate_take, candidate
                        left = middle + 1
                    else:
                        right = middle - 1
                if take == 0:
                    raise LLMError(
                        "INPUT_TOO_LARGE", "Một lượt hội thoại quá lớn cho model summary"
                    )
            elif await self.measure_text_tokens(
                prompt, settings.max_summary_input_tokens, "summary"
            ) > settings.max_summary_input_tokens:
                raise LLMError("INPUT_TOO_LARGE", "Summary cũ quá lớn để nén")

            context = ChatContext(system_instruction=SUMMARY_PROMPT, contents=[
                types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            ])
            try:
                result = await self.generate_once(context, operation="summary")
            except LLMError as error:
                current_model = route_model("summary", None, settings)
                fallback = fallback_model(current_model, "summary", settings)
                if not error.retryable or error.had_delta or not fallback:
                    raise
                result = await self.generate_once(
                    context, operation="summary", model_override=fallback
                )
            summary = result.text
            pending = pending[take:]
        return summary
