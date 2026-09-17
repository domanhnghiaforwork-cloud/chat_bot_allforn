from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Message


async def load_history(session: AsyncSession, conversation_id: UUID) -> list[Message]:
    result = await session.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        # Bản ghi cũ có thể trùng created_at; "user" phải đứng trước "assistant".
        .order_by(Message.created_at, Message.role.desc(), Message.id)
    )
    return list(result)
