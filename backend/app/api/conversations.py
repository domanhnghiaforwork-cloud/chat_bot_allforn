from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.conversation import ConversationDetail, ConversationResponse
from app.services import conversation as service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create(session: AsyncSession = Depends(get_session)) -> ConversationResponse:
    return await service.create_conversation(session)


@router.get("", response_model=list[ConversationResponse])
async def list_all(session: AsyncSession = Depends(get_session)) -> list[ConversationResponse]:
    return await service.list_conversations(session)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_one(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ConversationDetail:
    conversation = await service.get_conversation(session, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hội thoại")
    return conversation
