from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.conversation import MessageResponse


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    conversation_id: UUID
    message: str = Field(min_length=1)

    @field_validator("message")
    @classmethod
    def reject_local_command(cls, value: str) -> str:
        if value.startswith("/"):
            raise ValueError("Lệnh chat phải được xử lý cục bộ, không gửi tới model")
        return value


class ChatResponse(BaseModel):
    conversation_id: UUID
    answer: str
    user_message: MessageResponse
    assistant_message: MessageResponse
