from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config.model_catalog import model_limit
from app.config.settings import Settings
from app.rate_limit.redis_scripts import MODEL_RECONCILE_LUA, MODEL_RESERVE_LUA
from app.redis_client import get_redis


@dataclass(frozen=True, slots=True)
class QuotaReservation:
    allowed: bool
    tpm_key: str
    minute_window: int
    estimated_tokens: int
    enforced: bool = True


def _provider_day() -> tuple[str, int]:
    # Gemini RPD reset lúc nửa đêm Pacific, không phải UTC/local server.
    now = datetime.now(ZoneInfo("America/Los_Angeles"))
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return now.date().isoformat(), max(60, int((tomorrow - now).total_seconds()) + 3600)


class ModelLimiter:
    async def reserve(
        self, settings: Settings, model: str, estimated_tokens: int
    ) -> QuotaReservation:
        limit = model_limit(settings, model)
        if not settings.redis_url and not settings.async_chat_enabled and not settings.queue_enabled:
            return QuotaReservation(True, "", 0, estimated_tokens, enforced=False)
        # Thiếu quota là cấu hình production chưa hoàn chỉnh: fail-closed.
        if not limit.rpm or not limit.input_tpm or not limit.rpd:
            return QuotaReservation(False, "", 0, estimated_tokens)
        prefix = f"{settings.gemini_quota_project_id}:{model}"
        rpm_key = f"quota:{prefix}:rpm"
        tpm_key = f"quota:{prefix}:tpm"
        day, ttl = _provider_day()
        rpd_key = f"quota:{prefix}:rpd:{day}"
        result = await get_redis().eval(
            MODEL_RESERVE_LUA,
            3,
            rpm_key,
            tpm_key,
            rpd_key,
            max(1, int(limit.rpm * settings.safe_rpm_ratio)),
            max(1, int(limit.input_tpm * settings.safe_tpm_ratio)),
            max(1, int(limit.rpd * settings.safe_rpd_ratio)),
            max(0, estimated_tokens),
            ttl,
        )
        return QuotaReservation(bool(result[0]), tpm_key, int(result[4]), estimated_tokens)

    async def reconcile(self, reservation: QuotaReservation, actual_tokens: int) -> None:
        if not reservation.allowed or not reservation.enforced:
            return
        await get_redis().eval(
            MODEL_RECONCILE_LUA,
            1,
            reservation.tpm_key,
            reservation.minute_window,
            actual_tokens - reservation.estimated_tokens,
        )
