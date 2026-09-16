from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.conversation import MessageResponse


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    conversation_id: UUID
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    user_message: MessageResponse
    assistant_message: MessageResponse
