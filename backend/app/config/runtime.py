from dataclasses import dataclass
import asyncio
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.limits import EDITABLE_SETTINGS, validate_relations, validate_value
from app.config.settings import Settings, get_settings
from app.db.database import SessionLocal
from app.models import SystemSetting


@dataclass(frozen=True, slots=True)
class EffectiveSetting:
    key: str
    value: Any
    default: Any
    source: str
    value_type: str
    group: str
    minimum: float | None
    maximum: float | None
    requires_restart: bool
    choices: tuple[tuple[str | bool, str], ...] | None


async def effective_settings(session: AsyncSession | None = None) -> tuple[Settings, list[EffectiveSetting]]:
    env = get_settings()
    if session is None:
        async with SessionLocal() as own_session:
            loaded = (await own_session.scalars(select(SystemSetting))).all()
    else:
        loaded = (await session.scalars(select(SystemSetting))).all()
    rows = {row.key: row for row in loaded}

    values: dict[str, Any] = {}
    output: list[EffectiveSetting] = []
    for key, definition in EDITABLE_SETTINGS.items():
        default = getattr(env, definition.attr)
        row = rows.get(key)
        value = validate_value(definition, row.value_json) if row else default
        values[key] = value
        output.append(
            EffectiveSetting(
                key, value, default, "override" if row else "env",
                definition.value_type, definition.group,
                definition.minimum, definition.maximum, definition.requires_restart,
                definition.choices,
            )
        )
    validate_relations(values, env.max_history_summary_ratio)
    # model_copy giữ nguyên secret/URL từ ENV và chỉ thay allowlist vận hành.
    runtime = Settings.model_validate(
        {
            **env.model_dump(),
            **{EDITABLE_SETTINGS[key].attr: value for key, value in values.items()},
        }
    )
    return runtime, output


_cached: Settings | None = None
_cached_env: Settings | None = None
_expires_at = 0.0
_cache_version = 0
_cache_lock = asyncio.Lock()


def invalidate_runtime_settings() -> None:
    global _cached, _expires_at, _cache_version
    _cached = None
    _expires_at = 0.0
    _cache_version += 1


async def runtime_settings(session: AsyncSession | None = None) -> Settings:
    global _cached, _cached_env, _expires_at
    env = get_settings()
    if _cached is not None and _cached_env is env and time.monotonic() < _expires_at:
        return _cached
    async with _cache_lock:
        if _cached is not None and _cached_env is env and time.monotonic() < _expires_at:
            return _cached
        version = _cache_version
        settings, _ = await effective_settings(session)
        if version == _cache_version:
            _cached, _cached_env = settings, env
            _expires_at = time.monotonic() + env.runtime_settings_cache_seconds
        return settings
