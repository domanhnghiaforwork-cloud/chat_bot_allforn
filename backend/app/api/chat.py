from fastapi import APIRouter, Depends, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.db.database import get_session
from app.schemas.chat import ChatRequest, ChatResponse
from app.llm import LLMError
from app.rate_limit.conversation_lock import ConversationBusy
from app.redis_client import RedisUnavailable
from app.services.conversation import UserRateLimited, chat as chat_service
from app.services.generation import GenerationConflict, TooManyActiveGenerations

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    try:
        result = await chat_service(
            session,
            payload.conversation_id,
            current_user.id,
            payload.message,
        )
    except UserRateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "USER_RATE_LIMITED", "message": "Bạn gửi quá nhanh. Thử lại sau."},
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except (ConversationBusy, GenerationConflict, TooManyActiveGenerations) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONVERSATION_BUSY", "message": "Hội thoại đang có yêu cầu được xử lý"},
        ) from exc
    except (RedisUnavailable, RedisError, ConnectionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "QUEUE_UNAVAILABLE", "message": "Hệ thống điều phối tạm thời không khả dụng"},
        ) from exc
    except LLMError as exc:
        status_code = (
            status.HTTP_422_UNPROCESSABLE_ENTITY
            if exc.code in {"INPUT_TOO_LARGE", "SAFETY_BLOCKED"}
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": exc.public_message},
        ) from exc

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hội thoại",
        )

    answer, user_message, assistant_message = result
    return ChatResponse(
        conversation_id=payload.conversation_id,
        answer=answer,
        user_message=user_message,
        assistant_message=assistant_message,
    )
