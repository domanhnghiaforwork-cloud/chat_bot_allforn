from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

from google.genai import errors as genai_errors


RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


@dataclass(slots=True)
class LLMError(RuntimeError):
    code: str
    public_message: str
    retryable: bool = False
    provider_status_code: int | None = None
    retry_after_seconds: int | None = None
    had_delta: bool = False

    def __str__(self) -> str:
        return self.public_message


def _retry_after(exc: genai_errors.APIError) -> int | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    value = headers.get("Retry-After") if headers else None
    if not value:
        return None
    try:
        return max(1, int(float(value)))
    except ValueError:
        try:
            return max(1, int((parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()))
        except (TypeError, ValueError):
            return None


def normalize_provider_error(exc: Exception, *, had_delta: bool = False) -> LLMError:
    if isinstance(exc, LLMError):
        exc.had_delta = exc.had_delta or had_delta
        return exc
    if isinstance(exc, genai_errors.APIError):
        status = int(exc.code or 0)
        provider_status = (exc.status or "").upper()
        if status == 429:
            code, message = "PROVIDER_RATE_LIMITED", "Dịch vụ AI đang quá tải quota"
        elif status in {401, 403}:
            code, message = "PROVIDER_AUTH_ERROR", "Cấu hình xác thực dịch vụ AI không hợp lệ"
        elif status == 404 or "MODEL" in provider_status:
            code, message = "MODEL_UNAVAILABLE", "Model AI hiện không khả dụng"
        elif status >= 500 or status == 408:
            code, message = "PROVIDER_UNAVAILABLE", "Dịch vụ AI tạm thời không khả dụng"
        elif status in {400, 422}:
            code, message = "INPUT_TOO_LARGE", "Dữ liệu gửi tới model không hợp lệ hoặc quá lớn"
        else:
            code, message = "INTERNAL_ERROR", "Không thể xử lý phản hồi từ dịch vụ AI"
        return LLMError(
            code,
            message,
            retryable=status in RETRYABLE_STATUS_CODES and not had_delta,
            provider_status_code=status,
            retry_after_seconds=_retry_after(exc),
            had_delta=had_delta,
        )
    return LLMError(
        "PROVIDER_UNAVAILABLE",
        "Không thể kết nối dịch vụ AI",
        retryable=not had_delta,
        had_delta=had_delta,
    )
