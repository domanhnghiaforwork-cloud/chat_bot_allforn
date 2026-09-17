from contextlib import asynccontextmanager

from google import genai
from google.genai import types

from app.config.settings import Settings


@asynccontextmanager
async def gemini_client(settings: Settings):
    """SDK chỉ được thực hiện một HTTP attempt; retry thuộc application."""
    client = genai.Client(
        api_key=settings.gemini_api_key,
        http_options=types.HttpOptions(
            timeout=int(settings.gemini_request_timeout_seconds * 1000),
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )
    async with client.aio as async_client:
        yield async_client
