from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Conversation, Message, utc_now
from app.memory.context_builder import build_context
from app.memory.history import load_history
from app.memory.summary import prepare_memory
from app.services.gemini import generate_reply


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
    )
    if not conversation:
        return None

    history = await load_history(session, conversation_id)
    memory = await prepare_memory(session, conversation_id, history, question)
    # Summary phải được lưu trước khi recent bị thu gọn khỏi context.
    await session.commit()
    context = build_context(
        memory.summary,
        memory.recent_messages,
        question,
    )
    answer = await generate_reply(context)

    created_at = utc_now()
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=question,
        created_at=created_at,
    )
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        created_at=created_at + timedelta(microseconds=1),
    )
    session.add_all([user_message, assistant_message])
    if not history:
        conversation.title = question[:117] + ("..." if len(question) > 117 else "")
    conversation.updated_at = utc_now()
    await session.commit()
    await session.refresh(user_message)
    await session.refresh(assistant_message)

    return answer, user_message, assistant_message
