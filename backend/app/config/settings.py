from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    max_output_tokens: int = 1024
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/chatbot"
    max_input_tokens: int = 8_000
    recent_message_limit: int = 10
    summary_batch_size: int = 6

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
