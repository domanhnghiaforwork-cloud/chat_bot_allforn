from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationRequest, utc_now
from app.models.generation_request import ACTIVE_GENERATION_STATUSES


async def get_owned(
    session: AsyncSession, request_id: UUID, user_id: UUID, *, lock: bool = False
) -> GenerationRequest | None:
    query = select(GenerationRequest).where(
        GenerationRequest.id == request_id, GenerationRequest.user_id == user_id
    )
    if lock:
        query = query.with_for_update()
    return await session.scalar(query)


async def get_by_id(session: AsyncSession, request_id: UUID) -> GenerationRequest | None:
    return await session.get(GenerationRequest, request_id)


async def get_by_client(
    session: AsyncSession, user_id: UUID, client_request_id: UUID
) -> GenerationRequest | None:
    return await session.scalar(
        select(GenerationRequest).where(
            GenerationRequest.user_id == user_id,
            GenerationRequest.client_request_id == client_request_id,
        )
    )


async def get_active_for_conversation(
    session: AsyncSession, user_id: UUID, conversation_id: UUID
) -> GenerationRequest | None:
    return await session.scalar(
        select(GenerationRequest)
        .where(
            GenerationRequest.user_id == user_id,
            GenerationRequest.conversation_id == conversation_id,
            GenerationRequest.status.in_(ACTIVE_GENERATION_STATUSES),
        )
        .order_by(GenerationRequest.created_at.desc())
    )


async def active_count(session: AsyncSession, user_id: UUID) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(GenerationRequest).where(
                GenerationRequest.user_id == user_id,
                GenerationRequest.status.in_(ACTIVE_GENERATION_STATUSES),
            )
        )
        or 0
    )


async def claim(session: AsyncSession, request_id: UUID) -> GenerationRequest | None:
    result = await session.execute(
        update(GenerationRequest)
        .where(
            GenerationRequest.id == request_id,
            # PENDING hợp lệ khi process chết sau XADD nhưng trước khi cập nhật QUEUED.
            GenerationRequest.status.in_(("PENDING", "QUEUED", "RETRYING")),
        )
        .values(
            status="GENERATING",
            started_at=func.coalesce(GenerationRequest.started_at, utc_now()),
            updated_at=utc_now(),
            attempt_count=GenerationRequest.attempt_count + 1,
        )
        .returning(GenerationRequest)
    )
    return result.scalar_one_or_none()
