from app.config.settings import Settings


def route_model(operation: str, requested: str | None, settings: Settings) -> str:
    if operation == "summary":
        return settings.effective_summary_model
    if requested == "advanced":
        return settings.effective_advanced_model
    return settings.effective_default_model
