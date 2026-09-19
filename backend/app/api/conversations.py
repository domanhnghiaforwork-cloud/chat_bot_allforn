from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.db.database import get_session
from app.schemas.conversation import (
    ConversationDetail,
    ConversationResponse,
    ConversationTokenUsage,
)
from app.services import conversation as service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ConversationResponse:
    return await service.create_conversation(session, current_user.id)


@router.get("", response_model=list[ConversationResponse])
async def list_all(
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[ConversationResponse]:
    return await service.list_conversations(session, current_user.id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_one(
    conversation_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ConversationDetail:
    conversation = await service.get_conversation(
        session, conversation_id, current_user.id
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hội thoại")
    return conversation


@router.get(
    "/{conversation_id}/token-usage",
    response_model=ConversationTokenUsage,
)
async def get_token_usage(
    conversation_id: UUID,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ConversationTokenUsage:
    usage = await service.get_conversation_token_usage(
        session, conversation_id, current_user.id
    )
    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy hội thoại",
        )
    return ConversationTokenUsage.model_validate(usage)
