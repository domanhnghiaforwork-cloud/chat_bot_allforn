from dataclasses import asdict
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminUser
from app.config.limits import (
    EDITABLE_SETTINGS,
    EditableSetting,
    InvalidSetting,
    validate_relations,
    validate_value,
)
from app.config.runtime import effective_settings, runtime_settings
from app.config.settings import get_settings
from app.db.database import get_session
from app.models import AdminAuditLog, GenerationRequest, ModelUsage, SystemSetting, utc_now
from app.queue.manager import QueueManager
from app.schemas.admin import SettingDelete, SettingUpdate, SettingsBatchUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


async def _locked_setting_values(session: AsyncSession) -> dict[str, object]:
    # Serialize thay đổi cấu hình để hai admin không cùng tạo quan hệ retry sai.
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended('v4.2:settings', 0))")
    )
    env = get_settings()
    values = {
        key: getattr(env, definition.attr)
        for key, definition in EDITABLE_SETTINGS.items()
    }
    rows = list(await session.scalars(select(SystemSetting)))
    for row in rows:
        definition = EDITABLE_SETTINGS.get(row.key)
        if definition:
            values[row.key] = validate_value(definition, row.value_json)
    return values


async def _persist_setting(
    session: AsyncSession,
    key: str,
    value: object,
    value_type: str,
    admin: AdminUser,
    reason: str,
    reset: bool = False,
) -> SystemSetting | None:
    row = await session.get(SystemSetting, key, with_for_update=True)
    old_value = row.value_json if row else None
    if reset:
        if row:
            await session.delete(row)
    elif row:
        row.value_json = value
        row.value_type = value_type
        row.updated_by = admin.id
        row.updated_at = utc_now()
        row.version += 1
    else:
        row = SystemSetting(
            key=key,
            value_json=value,
            value_type=value_type,
            updated_by=admin.id,
        )
        session.add(row)
    session.add(
        AdminAuditLog(
            admin_id=admin.id,
            action="setting_reset" if reset else "setting_update",
            target=key,
            old_value=old_value,
            new_value=None if reset else value,
            reason=reason,
        )
    )
    return row


@router.get("/settings")
async def list_settings(admin: AdminUser):
    _, settings = await effective_settings()
    env = get_settings()
    return {
        "settings": [asdict(item) for item in settings],
        # Chỉ trả trạng thái, tuyệt đối không trả plaintext secret/URL.
        "secrets": {
            "DATABASE_URL": bool(env.database_url),
            "REDIS_URL": bool(env.redis_url),
            "JWT_SECRET_KEY": bool(env.jwt_secret_key),
            "GEMINI_API_KEY": bool(env.gemini_api_key),
        },
    }


@router.patch("/settings")
async def update_settings_batch(
    payload: SettingsBatchUpdate,
    admin: AdminUser,
    session: AsyncSession = Depends(get_session),
):
    env = get_settings()
    parsed: list[tuple[str, object, EditableSetting, bool]] = []
    try:
        candidate = await _locked_setting_values(session)
        for change in payload.changes:
            definition = EDITABLE_SETTINGS.get(change.key)
            if not definition:
                raise InvalidSetting(f"{change.key} không thuộc allowlist")
            value = (
                getattr(env, definition.attr)
                if change.reset
                else validate_value(definition, change.value)
            )
            candidate[change.key] = value
            parsed.append((change.key, value, definition, change.reset))
        validate_relations(candidate, env.max_history_summary_ratio)
    except InvalidSetting as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    for key, value, definition, reset in parsed:
        await _persist_setting(
            session, key, value, definition.value_type, admin, payload.reason, reset
        )
    await session.commit()
    return {"updated": [key for key, _, _, _ in parsed]}


@router.patch("/settings/{key}")
async def update_setting(
    key: str,
    payload: SettingUpdate,
    admin: AdminUser,
    session: AsyncSession = Depends(get_session),
):
    env = get_settings()
    definition = EDITABLE_SETTINGS.get(key)
    if not definition:
        raise HTTPException(status_code=404, detail="Cấu hình không thuộc allowlist")
    try:
        value = validate_value(definition, payload.value)
        candidate = await _locked_setting_values(session)
        candidate[key] = value
        validate_relations(candidate, env.max_history_summary_ratio)
    except InvalidSetting as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    row = await _persist_setting(
        session, key, value, definition.value_type, admin, payload.reason
    )
    await session.commit()
    assert row is not None
    return {"key": key, "value": value, "source": "override", "version": row.version}


@router.delete("/settings/{key}")
async def reset_setting(
    key: str,
    payload: SettingDelete,
    admin: AdminUser,
    session: AsyncSession = Depends(get_session),
):
    definition = EDITABLE_SETTINGS.get(key)
    if not definition:
        raise HTTPException(status_code=404, detail="Cấu hình không thuộc allowlist")
    try:
        candidate = await _locked_setting_values(session)
        candidate[key] = getattr(get_settings(), definition.attr)
        validate_relations(candidate, get_settings().max_history_summary_ratio)
    except InvalidSetting as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    await _persist_setting(
        session,
        key,
        getattr(get_settings(), definition.attr),
        definition.value_type,
        admin,
        payload.reason,
        reset=True,
    )
    await session.commit()
    return {"key": key, "source": "env", "value": getattr(get_settings(), definition.attr)}


@router.get("/audit-logs")
async def audit_logs(
    admin: AdminUser,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    rows = list(
        await session.scalars(
            select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(limit)
        )
    )
    return [
        {
            "id": row.id,
            "admin_id": row.admin_id,
            "action": row.action,
            "target": row.target,
            "old_value": row.old_value,
            "new_value": row.new_value,
            "reason": row.reason,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/overview")
async def overview(
    admin: AdminUser,
    session: AsyncSession = Depends(get_session),
):
    statuses = dict(
        (await session.execute(
            select(GenerationRequest.status, func.count())
            .group_by(GenerationRequest.status)
        )).all()
    )
    since = utc_now() - timedelta(hours=24)
    usage = (await session.execute(
        select(
            func.coalesce(func.sum(ModelUsage.actual_input_tokens), 0),
            func.coalesce(func.sum(ModelUsage.output_tokens), 0),
            func.count(ModelUsage.id),
        ).where(ModelUsage.created_at >= since)
    )).one()
    try:
        queue_depth = await QueueManager().depth()
    except Exception:
        queue_depth = None
    settings = await runtime_settings()
    return {
        "queue_depth": queue_depth,
        "generation_statuses": statuses,
        "usage_24h": {
            "input_tokens": usage[0], "output_tokens": usage[1], "attempts": usage[2]
        },
        "models": {
            "default": settings.effective_default_model,
            "summary": settings.effective_summary_model,
            "advanced": settings.effective_advanced_model,
        },
    }
