from dataclasses import dataclass
from typing import Any, Literal

from pydantic import TypeAdapter, ValidationError

from app.config.model_catalog import MODEL_CHOICES


SettingType = Literal["string", "integer", "number", "boolean"]


@dataclass(frozen=True, slots=True)
class EditableSetting:
    key: str
    attr: str
    value_type: SettingType
    group: str
    minimum: float | None = None
    maximum: float | None = None
    requires_restart: bool = False
    choices: tuple[tuple[str | bool, str], ...] | None = None


def _item(
    key: str,
    value_type: SettingType,
    group: str,
    minimum: float | None = None,
    maximum: float | None = None,
    requires_restart: bool = False,
    choices: tuple[tuple[str | bool, str], ...] | None = None,
) -> EditableSetting:
    return EditableSetting(
        key, key.lower(), value_type, group, minimum, maximum, requires_restart, choices
    )


# Allowlist cố ý không có secret hoặc URL hạ tầng.
EDITABLE_SETTINGS = {
    item.key: item
    for item in (
        _item("CHAT_CONTEXT_WINDOW_TOKENS", "integer", "Token Limits", 100),
        _item("SUMMARY_CONTEXT_WINDOW_TOKENS", "integer", "Token Limits", 100),
        _item("MAX_CONVERSATION_TOKENS", "integer", "Token Limits", 1),
        _item("DEFAULT_MODEL_NAME", "string", "Model/Quota", choices=MODEL_CHOICES),
        _item("SUMMARY_MODEL_NAME", "string", "Model/Quota", choices=MODEL_CHOICES),
        _item("ADVANCED_MODEL_NAME", "string", "Model/Quota", choices=MODEL_CHOICES),
        *(
            _item(key, "integer", "Model/Quota", 1)
            for key in (
                "DEFAULT_MODEL_RPM", "DEFAULT_MODEL_INPUT_TPM", "DEFAULT_MODEL_RPD",
                "SUMMARY_MODEL_RPM", "SUMMARY_MODEL_INPUT_TPM", "SUMMARY_MODEL_RPD",
                "ADVANCED_MODEL_RPM", "ADVANCED_MODEL_INPUT_TPM", "ADVANCED_MODEL_RPD",
            )
        ),
        _item("SAFE_RPM_RATIO", "number", "Model/Quota", 0.01, 1),
        _item("SAFE_TPM_RATIO", "number", "Model/Quota", 0.01, 1),
        _item("SAFE_RPD_RATIO", "number", "Model/Quota", 0.01, 1),
        _item("EXACT_TOKEN_COUNT_THRESHOLD", "number", "Model/Quota", 0.5, 1),
        _item(
            "FALLBACK_ENABLED",
            "boolean",
            "Model/Quota",
            choices=((True, "Bật"), (False, "Tắt")),
        ),
        _item("USER_RATE_CAPACITY", "integer", "Rate Limit", 1),
        _item("USER_RATE_REFILL_TOKENS", "integer", "Rate Limit", 1),
        _item("USER_RATE_REFILL_SECONDS", "integer", "Rate Limit", 1),
        _item("MAX_ACTIVE_GENERATIONS_PER_USER", "integer", "Rate Limit", 1),
        _item("MAX_QUEUE_SIZE", "integer", "Queue", 1),
        _item("MAX_QUEUE_WAIT_SECONDS", "integer", "Queue", 1),
        _item("QUEUE_EVENT_TTL_SECONDS", "integer", "Queue", 1),
        _item("QUEUE_JOB_MAX_ATTEMPTS", "integer", "Queue", 1),
        _item("WORKER_CONCURRENCY", "integer", "Queue", 1, 128, True),
        _item("WORKER_LEASE_SECONDS", "integer", "Queue", 6),
        _item("GEMINI_REQUEST_TIMEOUT_SECONDS", "number", "Retry", 1),
        _item("GEMINI_MAX_RETRY_ATTEMPTS", "integer", "Retry", 1, 10),
        _item("GEMINI_MAX_RETRY_ELAPSED_SECONDS", "number", "Retry", 1),
        _item("GEMINI_RETRY_INITIAL_DELAY_SECONDS", "number", "Retry", 0.1),
        _item("GEMINI_RETRY_MAX_DELAY_SECONDS", "number", "Retry", 0.1),
    )
}


class InvalidSetting(ValueError):
    pass


def validate_value(definition: EditableSetting, value: Any) -> Any:
    adapters = {
        "string": TypeAdapter(str),
        "integer": TypeAdapter(int),
        "number": TypeAdapter(float),
        "boolean": TypeAdapter(bool),
    }
    try:
        parsed = adapters[definition.value_type].validate_python(value, strict=True)
    except ValidationError as exc:
        raise InvalidSetting(f"{definition.key} sai kiểu {definition.value_type}") from exc
    if isinstance(parsed, str) and not parsed.strip():
        raise InvalidSetting(f"{definition.key} không được để trống")
    if definition.choices and parsed not in {choice[0] for choice in definition.choices}:
        allowed = ", ".join(str(choice[0]) for choice in definition.choices)
        raise InvalidSetting(f"{definition.key} chỉ chấp nhận: {allowed}")
    if definition.key.endswith("MODEL_NAME") and "latest" in parsed.lower():
        raise InvalidSetting(f"{definition.key} phải pin model ID, không dùng alias latest")
    if definition.minimum is not None and parsed < definition.minimum:
        raise InvalidSetting(f"{definition.key} phải >= {definition.minimum}")
    if definition.maximum is not None and parsed > definition.maximum:
        raise InvalidSetting(f"{definition.key} phải <= {definition.maximum}")
    return parsed.strip() if isinstance(parsed, str) else parsed


def validate_relations(
    values: dict[str, Any], max_history_summary_ratio: float
) -> None:
    chat_context = values["CHAT_CONTEXT_WINDOW_TOKENS"]
    summary_context = values["SUMMARY_CONTEXT_WINDOW_TOKENS"]
    max_conversation = values["MAX_CONVERSATION_TOKENS"]
    summary_output = int(chat_context * max_history_summary_ratio)
    if summary_context <= summary_output:
        raise InvalidSetting(
            "Summary context window phải lớn hơn ngân sách output summary"
        )
    if max_conversation < chat_context:
        raise InvalidSetting(
            "Max token cuộc hội thoại phải lớn hơn hoặc bằng chat context window"
        )

    initial = values["GEMINI_RETRY_INITIAL_DELAY_SECONDS"]
    maximum = values["GEMINI_RETRY_MAX_DELAY_SECONDS"]
    elapsed = values["GEMINI_MAX_RETRY_ELAPSED_SECONDS"]
    timeout = values["GEMINI_REQUEST_TIMEOUT_SECONDS"]
    if initial > maximum:
        raise InvalidSetting("Retry initial delay không được lớn hơn max delay")
    if maximum > elapsed:
        raise InvalidSetting("Retry max delay không được lớn hơn tổng thời gian retry")
    if timeout > elapsed:
        raise InvalidSetting("Timeout một attempt không được lớn hơn tổng thời gian retry")


CIRCUIT_FAILURE_THRESHOLD = 5
CIRCUIT_OPEN_SECONDS = 30
