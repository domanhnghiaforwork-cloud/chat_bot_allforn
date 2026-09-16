from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.models import ConversationSummary, Message, utc_now
from app.services.gemini import generate_summary


async def refresh_summary(
    session: AsyncSession,
    conversation_id: UUID,
    messages: list[Message],
) -> None:
    settings = get_settings()
    summary = await session.get(ConversationSummary, conversation_id)
    summarized_count = summary.summarized_message_count if summary else 0
    target_count = max(0, len(messages) - settings.recent_message_limit)

    # Tóm tắt theo lô để không gọi Gemini sau mọi tin nhắn.
    if target_count - summarized_count < settings.summary_batch_size:
        return

    content = await generate_summary(
        summary.content if summary else "",
        messages[summarized_count:target_count],
    )
    if summary:
        summary.content = content
        summary.summarized_message_count = target_count
        summary.updated_at = utc_now()
    else:
        session.add(
            ConversationSummary(
                conversation_id=conversation_id,
                content=content,
                summarized_message_count=target_count,
            )
        )
