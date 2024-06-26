import os
from typing import Any

from pathlib import Path

from loguru import logger
from pydantic_settings import BaseSettings


class CustomSettings(BaseSettings):

    ALLOWED_HOSTS: Any
    ORIGINS:list
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
    SUPERUSER_USER_TYPE: str
    ADMIN_USER_TYPE: str
    COMMISSIONER_USER_TYPE: str
    HEAD_OF_UNIT_USER_TYPE: str
    PUBLIC_USER_TYPE: str
    PUBLIC_FRONTEND_BASE_URL: str
    COURT_SYSTEM_FRONTEND_BASE_URL: str
    ADMIN_FRONTEND_BASE_URL: str
    VERIFY_EMAIL_LINK: str
    OPERATIONS_INVITE_TEMPLATE_ID: str
    JWT_EXPIRE_MINUTES: int
    RESET_PASSWORD_URL:str
    SENDER_NAME:str
    ACCEPT_INVITE_URL:str



    class Config:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        env_file = os.path.join(base_dir, "env_files", ".env")
        env_file_encoding = "utf-8"
