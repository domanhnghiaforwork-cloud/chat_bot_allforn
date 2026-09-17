from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config.settings import Settings


# Danh sách model được phép chọn trong production; dùng ID ổn định, không dùng alias latest.
MODEL_CHOICES = (
    ("gemini-3.5-flash-lite", "Gemini 3.5 Flash-Lite"),
    ("gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite"),
)
SUPPORTED_MODEL_IDS = frozenset(value for value, _ in MODEL_CHOICES)


@dataclass(frozen=True, slots=True)
class ModelLimit:
    name: str
    rpm: int | None
    input_tpm: int | None
    rpd: int | None


def model_limit(settings: "Settings", model: str) -> ModelLimit:
    """Chỉ ánh xạ cấu hình; tuyệt đối không hard-code quota của Google."""
    candidates = (
        ModelLimit(
            settings.effective_default_model,
            settings.default_model_rpm,
            settings.default_model_input_tpm,
            settings.default_model_rpd,
        ),
        ModelLimit(
            settings.effective_advanced_model,
            settings.advanced_model_rpm,
            settings.advanced_model_input_tpm,
            settings.advanced_model_rpd,
        ),
        ModelLimit(
            settings.effective_summary_model,
            settings.summary_model_rpm,
            settings.summary_model_input_tpm,
            settings.summary_model_rpd,
        ),
    )
    return next((item for item in candidates if item.name == model), candidates[0])
