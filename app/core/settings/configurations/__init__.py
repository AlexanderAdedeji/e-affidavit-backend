import logging
import sys

from app.core.settings.configurations.base import CustomSettings
from app.core.settings.configurations.production import ProductionSettings

from app.core.settings.logging import InterceptHandler
from app.core.settings.configurations.local import LocalSettings
from loguru import logger

if True:
    settings = LocalSettings()
else:
    settings = ProductionSettings()



LOGGING_LEVEL = logging.DEBUG if settings.DEBUG else logging.INFO
LOGGERS = ("uvicorn.asgi", "uvicorn.access")

logging.getLogger().handlers = [InterceptHandler()]
for logger_name in LOGGERS:
    logging_logger = logging.getLogger(logger_name)
    logging_logger.handlers = [InterceptHandler(level=LOGGING_LEVEL)]

logger.configure(handlers=[{"sink": sys.stderr, "level": LOGGING_LEVEL}])
