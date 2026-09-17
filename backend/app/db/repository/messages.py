from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message


async def list_by_conversation(
    session: AsyncSession, conversation_id: UUID
) -> list[Message]:
    result = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        # Bản ghi cũ có thể trùng created_at; user phải đứng trước assistant.
        .order_by(Message.created_at, Message.role.desc(), Message.id)
    )
    return list(result)


async def add_pair(
    session: AsyncSession,
    conversation_id: UUID,
    question: str,
    answer: str,
    user_created_at: datetime,
    assistant_created_at: datetime,
) -> tuple[Message, Message]:
    user_message = Message(
        conversation_id=conversation_id,
        role="user",
        content=question,
        created_at=user_created_at,
    )
    assistant_message = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        created_at=assistant_created_at,
    )
    session.add_all([user_message, assistant_message])
    await session.flush()
    return user_message, assistant_message
