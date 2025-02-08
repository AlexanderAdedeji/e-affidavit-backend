# app/core/settings/handler.py
import sys
import os
from pathlib import Path
from typing import Optional
from loguru import logger
from app.core.settings.logs.mongo_log_sink import mongo_sink

class LoggerConfig:
    def __init__(self, log_dir: Optional[str] = None, log_file: str = "app.log"):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.log_dir = Path(log_dir) if log_dir else self.project_root / "logs"
        self.log_file_path = self.log_dir / log_file

        # Ensure the log directory exists.
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._configure_logger()

    def _configure_logger(self):
        try:
            logger.remove()  # Remove default handlers
            
            # Console Logging
            logger.add(
                sys.stdout,
                format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                       "<level>{level: <8}</level> | "
                       "[Request ID: {extra[request_id]}] "
                       "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                       "<level>{message}</level>",
                level=os.getenv("LOG_LEVEL", "INFO"),
                colorize=True,
                enqueue=True,
            )

            # File Logging
            logger.add(
                self.log_file_path,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                rotation=os.getenv("LOG_ROTATION", "10 MB"),
                retention=os.getenv("LOG_RETENTION", "10 days"),
                compression=os.getenv("LOG_COMPRESSION", "zip"),
                level=os.getenv("LOG_FILE_LEVEL", "INFO"),
                enqueue=True,
            )

            # Error Logs
            logger.add(
                self.log_dir / "error.log",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
                rotation="5 MB",
                retention="7 days",
                compression="zip",
                level="ERROR",
                enqueue=True,
            )

            # JSON Formatted Logs
            logger.add(
                self.log_dir / "app.json",
                serialize=True,
                rotation="10 MB",
                retention="30 days",
                compression="zip",
                level=os.getenv("LOG_FILE_LEVEL", "INFO"),
                enqueue=True,
            )
            logger.add(
                mongo_sink,
                level="INFO",  # adjust as needed (e.g., INFO and above)
                enqueue=True,
                backtrace=True,
                diagnose=True,
            )

        except Exception as e:
            logger.error(f"Failed to configure logger: {e}")


LoggerConfig()
logger = logger  
