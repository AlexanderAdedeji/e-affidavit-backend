from pydantic_settings import BaseSettings
from pydantic import Field
import os


class CustomSettings(BaseSettings):
    # General Settings
    ALLOWED_HOSTS: str = Field(..., description="Comma-separated list of allowed hosts")
    ALLOWED_ORIGINS: str = Field(
        ..., description="Comma-separated list of allowed CORS origins"
    )
    ALLOWED_METHODS: str = Field(
        ..., description="Comma-separated list of allowed HTTP methods"
    )
    SECRET_KEY: str = Field(
        ..., env="SECRET_KEY", description="Secret key for the application"
    )
    RESET_TOKEN_EXPIRE_MINUTES: int = Field(
        60, description="Reset token expiration time in minutes"
    )
    PROJECT_NAME: str = Field("E-Affidavit Server", description="Project name")
    API_URL_PREFIX: str = Field(..., description="API URL prefix")
    VERSION: str = Field("0.1.0", description="API version")
    DEBUG: bool = Field(False, description="Debug mode")

    # Database Settings
    POSTGRES_DB_URL: str = Field(
        ..., env="POSTGRES_DB_URL", description="PostgreSQL database URL"
    )
    MONGO_DB_URL: str = Field(
        ..., env="MONGO_DB_URL", description="MongoDB database URL"
    )
    MONGO_DB_NAME: str = Field(
        ..., env="MONGO_DB_NAME", description="MongoDB database name"
    )

    # JWT and Security Settings
    JWT_TOKEN_PREFIX: str = Field(..., description="Prefix for JWT tokens")
    JWT_ALGORITHM: str = Field(..., description="Algorithm used for JWT tokens")
    JWT_EXPIRE_MINUTES: int = Field(..., description="JWT token expiration in minutes")
    HEADER_KEY: str = Field(..., description="Header key for authentication")
    API_KEY_AUTH_ENABLED: bool = Field(
        True, description="Enable or disable API key authentication"
    )

    # Email Configuration
    POSTMARK_API_TOKEN: str = Field(
        ...,
        env="POSTMARK_API_TOKEN",
        description="Postmark API token for sending emails",
    )
    DEFAULT_EMAIL_SENDER: str = Field(..., description="Default sender email address")
    RESET_PASSWORD_TEMPLATE_ID: str = Field(
        ..., description="Template ID for password reset emails"
    )
    DEACTIVATE_ACCOUNT_TEMPLATE_ID: str = Field(
        ..., description="Template ID for account deactivation emails"
    )
    CREATE_ACCOUNT_TEMPLATE_ID: str = Field(
        ..., description="Template ID for account creation emails"
    )
    VERIFY_EMAIL_TEMPLATE_ID: str = Field(
        ..., description="Template ID for email verification"
    )
    VERIFY_EMAIL_LINK: str = Field(..., description="Link for verifying emails")
    RESET_PASSWORD_URL: str = Field(..., description="URL for password reset page")
    SENDER_NAME: str = Field(..., description="Sender name for outgoing emails")
    ACCEPT_INVITE_URL: str = Field(..., description="URL for accepting an invitation")
    OPERATIONS_INVITE_TEMPLATE_ID: str = Field(
        ..., description="Template ID for operations invite emails"
    )

    # User Types
    SUPERUSER_USER_TYPE: str = Field(..., description="User type for superuser")
    ADMIN_USER_TYPE: str = Field(..., description="User type for admin")
    COMMISSIONER_USER_TYPE: str = Field(..., description="User type for commissioner")
    HEAD_OF_UNIT_USER_TYPE: str = Field(..., description="User type for head of unit")
    PUBLIC_USER_TYPE: str = Field(..., description="User type for public user")

    # Frontend URLs
    PUBLIC_FRONTEND_BASE_URL: str = Field(
        ..., description="Base URL for public frontend"
    )
    COURT_SYSTEM_FRONTEND_BASE_URL: str = Field(
        ..., description="Base URL for court system frontend"
    )
    ADMIN_FRONTEND_BASE_URL: str = Field(..., description="Base URL for admin frontend")

    # Payment Configuration
    PAYSTACK_SECRET_KEY: str = Field(..., description="Paystack secret key")
    PAYSTACK_VERIFY_PAYMENT_URL: str = Field(
        ..., description="Paystack verify payment URL"
    )

    class Config:
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "env_files", ".env"
        )
        env_file_encoding = "utf-8"
