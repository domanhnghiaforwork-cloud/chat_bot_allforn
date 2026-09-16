from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.conversation import chat as chat_service
from app.services.gemini import GeminiServiceError

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    try:
        result = await chat_service(session, payload.conversation_id, payload.message)
    except GeminiServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
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
