from pydantic import BaseModel


class PublicConfiguration(BaseModel):
    name_chatbot: str
