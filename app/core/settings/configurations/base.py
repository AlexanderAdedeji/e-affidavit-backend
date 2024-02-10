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

    
    JWT_TOKEN_PREFIX: str 
    # JWT_EXPIRE_MINUTES: int

    JWT_ALGORITHM: str
    HEADER_KEY: str
    API_KEY_AUTH_ENABLED: bool = True
    VERSION: str = "0.1.0"
    DEBUG: bool 

    class Config:
        logger.info("Environment file loaded from %s.", Path(__file__).parent)
        # Calculate the path to the .env file relative to the current file
        base_dir = os.path.dirname(os.path.dirname(__file__))  # This goes up two levels from the current file
        env_file = os.path.join(base_dir, 'env_files', '.env')
        env_file_encoding = 'utf-8'
    
        print(base_dir, env_file)
    

# To access the settings, you can use `CustomSettings().<setting>` like this
