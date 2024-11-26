from typing import Optional
from loguru import logger # type: ignore
import sys
from pathlib import Path
import os

class LoggerConfig:
    def __init__(self, log_dir: Optional[str] = None, log_file: str = "app.log"):

        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.log_dir = Path(log_dir) if log_dir else self.project_root / "logs"
        self.log_file_path = self.log_dir / log_file

        try:
            self.log_dir.mkdir(exist_ok=True)
        except Exception as e:
            print(f"Failed to create log directory: {e}", file=sys.stderr)

        self._configure_logger()

    def _configure_logger(self):
        try:
            logger.remove()

            # Add stdout logger
            logger.add(
                sys.stdout,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                level=os.getenv("LOG_LEVEL", "INFO"),
                colorize=True,
            )

            # Add file logger with rotation, retention, and compression
            logger.add(
                self.log_file_path,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                rotation=os.getenv("LOG_ROTATION", "10 MB"),  
                retention=os.getenv("LOG_RETENTION", "10 days"),  
                compression=os.getenv("LOG_COMPRESSION", "zip"), 
                level=os.getenv("LOG_FILE_LEVEL", "DEBUG"), 
            )
        except Exception as e:
            print(f"Failed to configure logger: {e}", file=sys.stderr)

    def get_logger(self):
        return logger


# Initialize logger configuration
log_config = LoggerConfig()
logger = log_config.get_logger()