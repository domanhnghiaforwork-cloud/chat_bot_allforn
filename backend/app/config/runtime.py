from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

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


async def effective_settings() -> tuple[Settings, list[EffectiveSetting]]:
    env = get_settings()
    async with SessionLocal() as session:
        rows = {
            row.key: row
            for row in (await session.scalars(select(SystemSetting))).all()
        }

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


async def runtime_settings() -> Settings:
    settings, _ = await effective_settings()
    return settings
