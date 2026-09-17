from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository import conversations, messages
from app.memory.context_builder import build_context
from app.memory.history import load_history
from app.memory.summary import prepare_memory
from app.models import Conversation, Message, utc_now
from app.services.gemini import generate_reply


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
    # Lọc user_id ngay trong query để không lộ hoặc dùng nhầm hội thoại người khác.
    conversation = await conversations.get_owned(session, conversation_id, user_id)
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
    user_message, assistant_message = await messages.add_pair(
        session,
        conversation_id,
        question,
        answer,
        created_at,
        created_at + timedelta(microseconds=1),
    )
    if not history:
        conversation.title = question[:117] + ("..." if len(question) > 117 else "")
    conversation.updated_at = utc_now()
    await session.commit()
    await session.refresh(user_message)
    await session.refresh(assistant_message)

    return answer, user_message, assistant_message
