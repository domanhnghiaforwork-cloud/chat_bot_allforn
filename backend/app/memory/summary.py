from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.prompts import SYSTEM_PROMPT
from app.config.settings import get_settings
from app.models import ConversationSummary, Message, utc_now
from app.memory.context_builder import build_context
from app.llm import LLMError, LLMGateway


@dataclass(slots=True)
class PreparedMemory:
    summary: str | None
    recent_messages: list[Message]


def _keep_complete_turn(messages: list[Message], count: int) -> int:
    """Không cắt rời câu hỏi user khỏi câu trả lời assistant ngay sau nó."""
    count = min(max(count, 0), len(messages))
    if (
        0 < count < len(messages)
        and messages[count - 1].role == "user"
        and messages[count].role == "assistant"
    ):
        count += 1
    return count


def _complete_turn_boundaries(messages: list[Message]) -> list[int]:
    """Các vị trí có thể cắt mà không tách user khỏi assistant ngay sau nó."""
    return [
        index
        for index in range(1, len(messages) + 1)
        if index == len(messages)
        or not (
            messages[index - 1].role == "user"
            and messages[index].role == "assistant"
        )
    ]


async def _summary_cut_for_target(
    messages: list[Message],
    target_tokens: int,
    max_tokens: int,
    max_count: int,
    gateway: LLMGateway,
) -> int:
    """Tìm prefix cũ cần tóm tắt để suffix mới về gần ngân sách mục tiêu."""
    boundaries = [0, *_complete_turn_boundaries(messages)]
    non_empty_cuts = boundaries[:-1]
    left, right = 0, len(non_empty_cuts) - 1
    selected: int | None = None

    # Token của suffix giảm theo điểm cắt, nên dùng binary search để giảm số lần
    # gọi tokenizer của model.
    while left <= right:
        middle = (left + right) // 2
        cut = non_empty_cuts[middle]
        remaining = messages[cut:]
        fits = (
            len(remaining) <= max_count
            and await gateway.measure_message_tokens(remaining, target_tokens) <= target_tokens
        )
        if fits:
            selected = cut
            right = middle - 1
        else:
            left = middle + 1

    if selected is not None:
        return selected

    # Nếu riêng lượt mới nhất đã lớn hơn target nhưng vẫn dưới mức tối đa,
    # giữ nguyên lượt đó thay vì đẩy toàn bộ ngữ cảnh gần nhất vào summary.
    latest_turn_start = boundaries[-2] if len(boundaries) > 1 else 0
    latest_turn = messages[latest_turn_start:]
    if (
        latest_turn
        and len(latest_turn) <= max_count
        and await gateway.measure_message_tokens(latest_turn, max_tokens) <= max_tokens
    ):
        return latest_turn_start

    return len(messages)


async def prepare_memory(
    session: AsyncSession,
    conversation_id: UUID,
    messages: list[Message],
    question: str,
    gateway: LLMGateway,
) -> PreparedMemory:
    settings = get_settings()
    system_tokens = await gateway.measure_text_tokens(
        SYSTEM_PROMPT, settings.max_system_prompt_tokens
    )
    question_tokens = await gateway.measure_text_tokens(
        question, settings.max_user_input_tokens
    )
    if system_tokens > settings.max_system_prompt_tokens:
        raise LLMError("INPUT_TOO_LARGE", "System Prompt vượt ngân sách token")
    if question_tokens > settings.max_user_input_tokens:
        raise LLMError("INPUT_TOO_LARGE", "Câu hỏi vượt ngân sách token")

    summary_row = await session.get(ConversationSummary, conversation_id)
    summary_text = summary_row.content if summary_row else ""
    summarized_count = summary_row.summarized_message_count if summary_row else 0
    # Đóng transaction đọc trước mọi lời gọi provider; không giữ connection DB khi chờ Gemini.
    await session.commit()
    recent = messages[summarized_count:]
    changed = False

    # Nén lại summary cũ nếu cấu hình token mới nhỏ hơn dữ liệu đã lưu.
    if (
        summary_text
        and await gateway.measure_text_tokens(
            summary_text, settings.max_history_summary_tokens, "summary"
        )
        > settings.max_history_summary_tokens
    ):
        summary_text = await gateway.generate_summary(summary_text, [])
        changed = True

    recent_tokens = await gateway.measure_message_tokens(
        recent, settings.max_history_recent_messages_tokens
    )
    exceeds_count = len(recent) > settings.recent_message_limit
    exceeds_tokens = recent_tokens > settings.max_history_recent_messages_tokens

    if exceeds_count or exceeds_tokens:
        summarize_count = await _summary_cut_for_target(
            recent,
            settings.target_history_recent_messages_tokens,
            settings.max_history_recent_messages_tokens,
            settings.recent_message_limit,
            gateway,
        )
        summary_text = await gateway.generate_summary(summary_text, recent[:summarize_count])
        if await gateway.measure_text_tokens(
            summary_text, settings.max_history_summary_tokens, "summary"
        ) > settings.max_history_summary_tokens:
            raise LLMError("INPUT_TOO_LARGE", "Summary vượt ngân sách token")
        summarized_count += summarize_count
        recent = recent[summarize_count:]
        changed = True

    if (
        summary_text
        and await gateway.measure_text_tokens(
            summary_text, settings.max_history_summary_tokens, "summary"
        )
        > settings.max_history_summary_tokens
    ):
        raise LLMError("INPUT_TOO_LARGE", "Summary vượt ngân sách token")

    # Kiểm tra tổng input thực tế, gồm cả role và phần nhãn summary.
    context = build_context(summary_text or None, recent, question)
    while await gateway.measure_context_tokens(
        context, settings.max_chat_input_tokens
    ) > settings.max_chat_input_tokens:
        if not recent:
            raise LLMError("INPUT_TOO_LARGE", "Không thể thu gọn context vào ngân sách input")
        # Nhánh dự phòng chỉ tóm tắt lượt hoàn chỉnh cũ nhất, không dùng batch cố định.
        summarize_count = _keep_complete_turn(recent, 1)
        summary_text = await gateway.generate_summary(summary_text, recent[:summarize_count])
        if await gateway.measure_text_tokens(
            summary_text, settings.max_history_summary_tokens, "summary"
        ) > settings.max_history_summary_tokens:
            raise LLMError("INPUT_TOO_LARGE", "Summary vượt ngân sách token")
        summarized_count += summarize_count
        recent = recent[summarize_count:]
        changed = True
        context = build_context(summary_text, recent, question)

    if changed:
        current_summary = await session.get(ConversationSummary, conversation_id)
        if current_summary:
            current_summary.content = summary_text
            current_summary.summarized_message_count = summarized_count
            current_summary.updated_at = utc_now()
        else:
            session.add(
                ConversationSummary(
                    conversation_id=conversation_id,
                    content=summary_text,
                    summarized_message_count=summarized_count,
                )
            )
        await session.commit()

    return PreparedMemory(summary=summary_text or None, recent_messages=recent)
