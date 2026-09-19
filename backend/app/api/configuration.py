from fastapi import APIRouter

from app.config.settings import get_settings
from app.schemas.configuration import PublicConfiguration

router = APIRouter(tags=["configuration"])


@router.get("/config", response_model=PublicConfiguration)
async def get_public_configuration() -> PublicConfiguration:
    return PublicConfiguration(name_chatbot=get_settings().name_chatbot)
