from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.db.repository import conversations, generations, messages
from app.models import GenerationRequest, Message, utc_now


class GenerationConflict(RuntimeError):
    pass


class TooManyActiveGenerations(RuntimeError):
    pass


async def create_request(
    session: AsyncSession,
    *,
    user_id: UUID,
    conversation_id: UUID,
    question: str,
    client_request_id: UUID,
    requested_model: str | None,
    settings: Settings,
) -> tuple[GenerationRequest | None, bool]:
    existing = await generations.get_by_client(session, user_id, client_request_id)
    if existing:
        return existing, False
    if not await conversations.get_owned(session, conversation_id, user_id):
        return None, False
    # Khóa giao dịch theo user để hai backend instance không cùng vượt ngưỡng active.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:user_id, 0))"),
        {"user_id": str(user_id)},
    )
    if await generations.active_count(session, user_id) >= settings.max_active_generations_per_user:
        raise TooManyActiveGenerations
    request = GenerationRequest(
        client_request_id=client_request_id,
        user_id=user_id,
        conversation_id=conversation_id,
        question=question,
        requested_model=requested_model,
        operation="chat",
        status="PENDING",
    )
    session.add(request)
    try:
        await session.commit()
        await session.refresh(request)
        return request, True
    except IntegrityError as exc:
        await session.rollback()
        existing = await generations.get_by_client(session, user_id, client_request_id)
        if existing:
            return existing, False
        raise GenerationConflict from exc


async def create_sync_request(
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
    question: str,
    settings: Settings,
) -> GenerationRequest | None:
    request, _ = await create_request(
        session,
        user_id=user_id,
        conversation_id=conversation_id,
        question=question,
        client_request_id=uuid4(),
        requested_model="default",
        settings=settings,
    )
    return request


async def finalize_success(
    session: AsyncSession, request_id: UUID, answer: str, model: str
) -> tuple[Message, Message] | None:
    request = await session.get(GenerationRequest, request_id, with_for_update=True)
    if not request or request.status in {"CANCELLED", "DONE"}:
        return None
    conversation = await conversations.get_owned(
        session, request.conversation_id, request.user_id
    )
    if not conversation:
        return None
    created_at = utc_now()
    user_message, assistant_message = await messages.add_pair(
        session,
        request.conversation_id,
        request.question,
        answer,
        created_at,
        created_at + timedelta(microseconds=1),
    )
    if conversation.title == "Cuộc trò chuyện mới":
        conversation.title = request.question[:117] + (
            "..." if len(request.question) > 117 else ""
        )
    conversation.updated_at = utc_now()
    request.status = "DONE"
    request.actual_model = model
    request.user_message_id = user_message.id
    request.assistant_message_id = assistant_message.id
    request.completed_at = utc_now()
    request.updated_at = utc_now()
    await session.commit()
    await session.refresh(user_message)
    await session.refresh(assistant_message)
    return user_message, assistant_message


async def fail_request(
    session: AsyncSession, request_id: UUID, code: str, message: str
) -> None:
    request = await session.get(GenerationRequest, request_id, with_for_update=True)
    if request and request.status not in {"DONE", "CANCELLED"}:
        request.status = "FAILED"
        request.error_code = code
        request.error_message = message
        request.completed_at = utc_now()
        request.updated_at = utc_now()
        await session.commit()
