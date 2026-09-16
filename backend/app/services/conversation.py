from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Conversation, Message, utc_now
from app.memory.context_builder import build_context
from app.memory.history import load_history
from app.memory.summary import refresh_summary
from app.services.gemini import GeminiServiceError, generate_reply


async def create_conversation(session: AsyncSession) -> Conversation:
    conversation = Conversation()
    session.add(conversation)
    await session.commit()
    await session.refresh(conversation)
    return conversation


async def list_conversations(session: AsyncSession) -> list[Conversation]:
    result = await session.scalars(
        select(Conversation).order_by(Conversation.updated_at.desc())
    )
    return list(result)


async def get_conversation(
    session: AsyncSession, conversation_id: UUID
) -> Conversation | None:
    return await session.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )


async def chat(
    session: AsyncSession, conversation_id: UUID, question: str
) -> tuple[str, Message, Message] | None:
    conversation = await session.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.summary))
    )
    if not conversation:
        return None

    history = await load_history(session, conversation_id)
    summary = conversation.summary
    summarized_count = summary.summarized_message_count if summary else 0
    context = build_context(
        summary.content if summary else None,
        history[summarized_count:],
        question,
    )
    answer = await generate_reply(context)

    user_message = Message(conversation_id=conversation_id, role="user", content=question)
    assistant_message = Message(
        conversation_id=conversation_id, role="assistant", content=answer
    )
    session.add_all([user_message, assistant_message])
    if not history:
        conversation.title = question[:117] + ("..." if len(question) > 117 else "")
    conversation.updated_at = utc_now()
    await session.commit()
    await session.refresh(user_message)
    await session.refresh(assistant_message)

    # Lỗi tóm tắt không được làm mất câu trả lời đã lưu thành công.
    try:
        await refresh_summary(
            session, conversation_id, [*history, user_message, assistant_message]
        )
        await session.commit()
    except GeminiServiceError:
        await session.rollback()

    return answer, user_message, assistant_message
