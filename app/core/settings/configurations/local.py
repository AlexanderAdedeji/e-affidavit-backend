from app.core.settings.configurations.base import CustomSettings


class LocalSettings(CustomSettings):
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
