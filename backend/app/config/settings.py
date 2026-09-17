from functools import lru_cache
from math import isclose

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Không đặt giá trị mặc định: toàn bộ cấu hình phải đến từ ENV.
    gemini_api_key: str
    gemini_model: str
    database_url: str

    chat_context_window_tokens: int = Field(gt=0)
    summary_context_window_tokens: int = Field(gt=0)
    max_input_ratio: float = Field(gt=0, le=1)
    max_system_prompt_ratio: float = Field(gt=0, le=1)
    max_user_input_ratio: float = Field(gt=0, le=1)
    max_history_summary_ratio: float = Field(gt=0, le=1)
    max_history_recent_messages_ratio: float = Field(gt=0, le=1)
    target_history_recent_messages_ratio: float = Field(gt=0, le=1)
    max_output_ratio: float = Field(gt=0, le=1)
    recent_message_limit: int = Field(gt=0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_token_ratios(self) -> "Settings":
        input_parts = (
            self.max_system_prompt_ratio
            + self.max_user_input_ratio
            + self.max_history_summary_ratio
            + self.max_history_recent_messages_ratio
        )
        if not isclose(input_parts, self.max_input_ratio):
            raise ValueError("Tổng tỷ lệ thành phần input phải bằng MAX_INPUT_RATIO")
        if not isclose(self.max_input_ratio + self.max_output_ratio, 1.0):
            raise ValueError("MAX_INPUT_RATIO + MAX_OUTPUT_RATIO phải bằng 1")
        if (
            self.target_history_recent_messages_ratio
            >= self.max_history_recent_messages_ratio
        ):
            raise ValueError(
                "TARGET_HISTORY_RECENT_MESSAGES_RATIO phải nhỏ hơn "
                "MAX_HISTORY_RECENT_MESSAGES_RATIO"
            )
        if self.max_history_summary_tokens >= self.summary_context_window_tokens:
            raise ValueError(
                "SUMMARY_CONTEXT_WINDOW_TOKENS phải lớn hơn ngân sách output summary"
            )
        return self

    def chat_token_budget(self, ratio: float) -> int:
        return int(self.chat_context_window_tokens * ratio)

    @property
    def max_chat_input_tokens(self) -> int:
        return self.chat_token_budget(self.max_input_ratio)

    @property
    def max_system_prompt_tokens(self) -> int:
        return self.chat_token_budget(self.max_system_prompt_ratio)

    @property
    def max_user_input_tokens(self) -> int:
        return self.chat_token_budget(self.max_user_input_ratio)

    @property
    def max_history_summary_tokens(self) -> int:
        return self.chat_token_budget(self.max_history_summary_ratio)

    @property
    def max_history_recent_messages_tokens(self) -> int:
        return self.chat_token_budget(self.max_history_recent_messages_ratio)

    @property
    def target_history_recent_messages_tokens(self) -> int:
        return self.chat_token_budget(self.target_history_recent_messages_ratio)

    @property
    def max_chat_output_tokens(self) -> int:
        return self.chat_token_budget(self.max_output_ratio)

    @property
    def max_summary_input_tokens(self) -> int:
        # Chừa sẵn chỗ cho output summary trong context window của model summary.
        return self.summary_context_window_tokens - self.max_history_summary_tokens


@lru_cache
def get_settings() -> Settings:
    return Settings()
