from app.core.settings.configurations.base import CustomSettings


class ProductionSettings(CustomSettings):
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
