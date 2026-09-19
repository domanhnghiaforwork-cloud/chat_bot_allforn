from functools import lru_cache
from math import isclose
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.model_catalog import SUPPORTED_MODEL_IDS


class Settings(BaseSettings):
    # Không đặt giá trị mặc định: toàn bộ cấu hình phải đến từ ENV.
    gemini_api_key: str
    gemini_model: str
    name_chatbot: str = Field(default="OLP AI", min_length=1, max_length=80)
    database_url: str
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"]
    access_token_expire_minutes: int = Field(gt=0)

    chat_context_window_tokens: int = Field(gt=0)
    summary_context_window_tokens: int = Field(gt=0)
    max_conversation_tokens: int = Field(gt=0)
    max_input_ratio: float = Field(gt=0, le=1)
    max_system_prompt_ratio: float = Field(gt=0, le=1)
    max_user_input_ratio: float = Field(gt=0, le=1)
    max_history_summary_ratio: float = Field(gt=0, le=1)
    max_history_recent_messages_ratio: float = Field(gt=0, le=1)
    target_history_recent_messages_ratio: float = Field(gt=0, le=1)
    max_output_ratio: float = Field(gt=0, le=1)
    recent_message_limit: int = Field(gt=0)
    exact_token_count_threshold: float = Field(default=0.95, gt=0, le=1)

    # V4.2 mặc định tắt luồng mới để có thể deploy schema trước rồi mới cutover.
    async_chat_enabled: bool = False
    legacy_sync_chat_enabled: bool = True
    queue_enabled: bool = False
    redis_url: str | None = None
    redis_socket_timeout_seconds: float = Field(default=2.0, gt=0)

    user_rate_capacity: int = Field(default=10, gt=0)
    user_rate_refill_tokens: int = Field(default=10, gt=0)
    user_rate_refill_seconds: int = Field(default=60, gt=0)
    max_active_generations_per_user: int = Field(default=3, gt=0)
    # Dùng range 1..1 để Pydantic parse được chuỗi "1" từ file .env.
    max_active_generations_per_conversation: int = Field(default=1, ge=1, le=1)

    max_queue_size: int = Field(default=1000, gt=0)
    max_queue_wait_seconds: int = Field(default=900, gt=0)
    queue_event_ttl_seconds: int = Field(default=3600, gt=0)
    queue_job_max_attempts: int = Field(default=4, gt=0)
    worker_concurrency: int = Field(default=4, gt=0)
    worker_lease_seconds: int = Field(default=60, gt=5)

    gemini_request_timeout_seconds: float = Field(default=60, gt=0)
    gemini_max_retry_attempts: int = Field(default=3, gt=0)
    gemini_max_retry_elapsed_seconds: float = Field(default=90, gt=0)
    gemini_retry_initial_delay_seconds: float = Field(default=1, gt=0)
    gemini_retry_max_delay_seconds: float = Field(default=20, gt=0)

    gemini_quota_project_id: str = "default"
    default_model_name: str | None = None
    default_model_rpm: int | None = Field(default=None, gt=0)
    default_model_input_tpm: int | None = Field(default=None, gt=0)
    default_model_rpd: int | None = Field(default=None, gt=0)
    advanced_model_name: str | None = None
    advanced_model_rpm: int | None = Field(default=None, gt=0)
    advanced_model_input_tpm: int | None = Field(default=None, gt=0)
    advanced_model_rpd: int | None = Field(default=None, gt=0)
    summary_model_name: str | None = None
    summary_model_rpm: int | None = Field(default=None, gt=0)
    summary_model_input_tpm: int | None = Field(default=None, gt=0)
    summary_model_rpd: int | None = Field(default=None, gt=0)
    safe_rpm_ratio: float = Field(default=0.9, gt=0, le=1)
    safe_tpm_ratio: float = Field(default=0.9, gt=0, le=1)
    safe_rpd_ratio: float = Field(default=0.9, gt=0, le=1)
    fallback_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("name_chatbot")
    @classmethod
    def validate_name_chatbot(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("NAME_CHATBOT không được để trống")
        return name

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
        if self.max_conversation_tokens < self.chat_context_window_tokens:
            raise ValueError(
                "MAX_CONVERSATION_TOKENS phải lớn hơn hoặc bằng "
                "CHAT_CONTEXT_WINDOW_TOKENS"
            )
        if self.async_chat_enabled and not self.queue_enabled:
            raise ValueError("ASYNC_CHAT_ENABLED yêu cầu QUEUE_ENABLED=true")
        if self.queue_enabled and not self.redis_url:
            raise ValueError("QUEUE_ENABLED yêu cầu REDIS_URL")
        if any(
            "latest" in model.lower()
            for model in (
                self.effective_default_model,
                self.effective_summary_model,
                self.effective_advanced_model,
            )
        ):
            raise ValueError("Production phải pin model ID, không dùng alias latest")
        unsupported = {
            model
            for model in (
                self.effective_default_model,
                self.effective_summary_model,
                self.effective_advanced_model,
            )
            if model not in SUPPORTED_MODEL_IDS
        }
        if unsupported:
            raise ValueError(
                "Model không được hỗ trợ: " + ", ".join(sorted(unsupported))
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

    @property
    def effective_default_model(self) -> str:
        return self.default_model_name or self.gemini_model

    @property
    def effective_summary_model(self) -> str:
        return self.summary_model_name or self.effective_default_model

    @property
    def effective_advanced_model(self) -> str:
        return self.advanced_model_name or self.effective_default_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
