import random

from app.config.settings import Settings
from app.llm.errors import LLMError


def retry_delay(error: LLMError, attempt: int, settings: Settings) -> float:
    if error.retry_after_seconds:
        # Không retry sớm hơn thời điểm provider yêu cầu.
        return float(error.retry_after_seconds)
    ceiling = min(
        settings.gemini_retry_max_delay_seconds,
        settings.gemini_retry_initial_delay_seconds * (2 ** max(0, attempt - 1)),
    )
    return random.uniform(0, ceiling)
