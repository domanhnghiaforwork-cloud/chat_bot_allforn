from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import messages
from app.models import Message


async def load_history(session: AsyncSession, conversation_id: UUID) -> list[Message]:
    return await messages.list_by_conversation(session, conversation_id)
