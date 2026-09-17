from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from redis.exceptions import RedisError
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.config.runtime import runtime_settings
from app.db.database import get_session
from app.db.repository import generations
from app.models import GenerationRequest, utc_now
from app.queue.events import publish_event, stream_events
from app.queue.manager import QueueFull, QueueManager
from app.rate_limit.user_limiter import UserLimiter
from app.schemas.generation import ChatJobAccepted, ChatJobRequest, GenerationResponse
from app.services.generation import (
    GenerationConflict,
    TooManyActiveGenerations,
    create_request,
)

router = APIRouter(tags=["generations"])


@router.post("/chat/jobs", response_model=ChatJobAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_chat_job(
    payload: ChatJobRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ChatJobAccepted:
    settings = await runtime_settings()
    if not settings.async_chat_enabled or not settings.queue_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Luồng chat bất đồng bộ chưa được bật",
        )
    try:
        # Request gửi lại phải lấy đúng job cũ và không tiêu thêm token rate-limit.
        generation = await generations.get_by_client(
            session, current_user.id, payload.client_request_id
        )
        created = False
        if not generation:
            limit = await UserLimiter().consume(current_user.id, settings)
            if not limit.allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"code": "USER_RATE_LIMITED", "message": "Bạn gửi quá nhanh. Thử lại sau."},
                    headers={"Retry-After": str(limit.retry_after_seconds)},
                )
            generation, created = await create_request(
                session,
                user_id=current_user.id,
                conversation_id=payload.conversation_id,
                question=payload.message,
                client_request_id=payload.client_request_id,
                requested_model=payload.model,
                settings=settings,
            )
        if not generation:
            raise HTTPException(status_code=404, detail="Không tìm thấy hội thoại")
        if not created and generation.status != "PENDING":
            return ChatJobAccepted(
                request_id=generation.id, status=generation.status, queue_position=None
            )
        queued = await QueueManager().enqueue(generation.id, settings.max_queue_size)
        queued_at = utc_now()
        updated = await session.execute(
            update(GenerationRequest)
            .where(
                GenerationRequest.id == generation.id,
                GenerationRequest.status == "PENDING",
            )
            .values(status="QUEUED", queued_at=queued_at, updated_at=queued_at)
        )
        await session.commit()
        await session.refresh(generation)
        if updated.rowcount:
            await publish_event(
                generation.id,
                "queued",
                {"status": "QUEUED", "queue_position": queued.position},
                settings.queue_event_ttl_seconds,
            )
        return ChatJobAccepted(
            request_id=generation.id,
            status=generation.status,
            queue_position=queued.position,
        )
    except QueueFull as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "QUEUE_FULL", "message": "Hàng đợi đang đầy"},
        ) from exc
    except (GenerationConflict, TooManyActiveGenerations) as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "CONVERSATION_BUSY", "message": "Hội thoại hoặc tài khoản đang có yêu cầu active"},
        ) from exc
    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "QUEUE_UNAVAILABLE", "message": "Hệ thống hàng đợi tạm thời không khả dụng"},
        ) from exc


@router.get("/generations/active", response_model=GenerationResponse | None)
async def active_generation(
    conversation_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    return await generations.get_active_for_conversation(
        session, current_user.id, conversation_id
    )


@router.get("/generations/{request_id}", response_model=GenerationResponse)
async def get_generation(
    request_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    generation = await generations.get_owned(session, request_id, current_user.id)
    if not generation:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")
    return generation


@router.delete("/generations/{request_id}", response_model=GenerationResponse)
async def cancel_generation(
    request_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
):
    generation = await generations.get_owned(
        session, request_id, current_user.id, lock=True
    )
    if not generation:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")
    if generation.status not in {"DONE", "FAILED", "CANCELLED"}:
        generation.status = "CANCELLED"
        generation.error_code = "CANCELLED"
        generation.error_message = "Yêu cầu đã được hủy"
        generation.completed_at = utc_now()
        generation.updated_at = utc_now()
        await session.commit()
        await QueueManager().complete(request_id)
        settings = await runtime_settings()
        await publish_event(
            request_id,
            "failed",
            {"status": "CANCELLED", "error_code": "CANCELLED"},
            settings.queue_event_ttl_seconds,
        )
    return generation


@router.get("/generations/{request_id}/events")
async def generation_events(
    request_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    cursor: str | None = Query(default=None),
):
    generation = await generations.get_owned(session, request_id, current_user.id)
    if not generation:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu")
    # StreamingResponse tồn tại lâu; đóng transaction đọc trước khi mở SSE.
    await session.rollback()
    return StreamingResponse(
        stream_events(request_id, last_event_id or cursor or "0-0"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
