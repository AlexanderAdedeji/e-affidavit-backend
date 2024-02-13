from passlib.context import CryptContext
from app.core.settings.configurations import settings

# Dynamic scheme configuration from settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AppSecurity:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def is_strong_password(password: str) -> bool:
        return (
            len(password) >= 8
            and any(c.isdigit() for c in password)
            and not password.isalnum()
        )

    @staticmethod
    def generate_reset_token(user_id: str) -> str:
        pass

    @staticmethod
    def verify_reset_token(token: str) -> bool:
        pass


security = AppSecurity()
