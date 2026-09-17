from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation


async def create(session: AsyncSession, user_id: UUID) -> Conversation:
    conversation = Conversation(user_id=user_id)
    session.add(conversation)
    await session.flush()
    return conversation


async def list_by_user(session: AsyncSession, user_id: UUID) -> list[Conversation]:
    result = await session.scalars(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result)


async def get_owned(
    session: AsyncSession,
    conversation_id: UUID,
    user_id: UUID,
    *,
    with_messages: bool = False,
) -> Conversation | None:
    query = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    )
    if with_messages:
        query = query.options(selectinload(Conversation.messages))
    return await session.scalar(query)
