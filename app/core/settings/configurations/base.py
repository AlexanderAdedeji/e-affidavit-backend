import os
from typing import Any

from pathlib import Path

from loguru import logger
from pydantic_settings import BaseSettings


class CustomSettings(BaseSettings):

    ALLOWED_HOSTS: Any

    SECRET_KEY: str
    RESET_TOKEN_EXPIRE_MINUTES: int = 60
    PROJECT_NAME: str = "E-Affidavit Server"
    API_URL_PREFIX: str
    POSTGRES_DB_URL: str
    MONGO_DB_URL: str
    JWT_TOKEN_PREFIX: str
    JWT_ALGORITHM: str
    HEADER_KEY: str
    API_KEY_AUTH_ENABLED: bool = True
    VERSION: str = "0.1.0"
    DEBUG: bool
    POSTMARK_API_TOKEN: str
    DEFAULT_EMAIL_SENDER: str
    RESET_PASSWORD_TEMPLATE_ID: str
    DEACTIVATE_ACCOUNT_TEMPLATE_ID: str
    CREATE_ACCOUNT_TEMPLATE_ID: str
    VERIFY_EMAIL_TEMPLATE_ID: str
    RESET_TOKEN_EXPIRE_MINUTES: str
    SUPERUSER_USER_TYPE:str
    ADMIN_USER_TYPE:str
    COMMISSIONER_USER_TYPE:str
    HEAD_OF_UNIT_USER_TYPE:str
    PUBLIC_USER_TYPE:str
    
    JWT_EXPIRE_MINUTES:int



    class Config:
        logger.info("Environment file loaded from %s.", Path(__file__).parent)
        # Calculate the path to the .env file relative to the current file
        base_dir = os.path.dirname(
            os.path.dirname(__file__)
        )  # This goes up two levels from the current file
        env_file = os.path.join(base_dir, "env_files", ".env")
        env_file_encoding = "utf-8"

        print(base_dir, env_file)


# To access the settings, you can use `CustomSettings().<setting>` like this
