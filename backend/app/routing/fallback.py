from app.config.settings import Settings


def fallback_model(current: str, operation: str, settings: Settings) -> str | None:
    if not settings.fallback_enabled:
        return None
    default = settings.effective_default_model
    if current != default and operation in {"chat", "summary"}:
        return default
    return None
