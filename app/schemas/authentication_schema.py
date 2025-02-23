import re
from typing import Annotated, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ChangePassword(BaseModel):
    old_password: Annotated[str, Field(...,min_length=8, max_length=128)]
    new_password: Annotated[str, Field(...,min_length=8, max_length=128)]

    @field_validator("new_password")
    def new_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError(
                "New password must contain at least one letter and one digit."
            )
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        return value


class UserUpdate(BaseModel):
    first_name: Optional[Annotated[str,Field(...,min_length=3, max_length=50)]]
    last_name: Optional[Annotated[str,Field(...,min_length=3, max_length=50)]]
    address: Optional[Annotated[str,Field( ...,min_length=3)]] = None
    phone: Optional[Annotated[str,Field(...,pattern=r"^\+?[1-9]\d{1,14}$]")]] = None
    password: Optional[Annotated[str,Field(...,min_length=8, max_length=128)]] = None

    @field_validator("first_name", "last_name")
    def names_must_be_alphabetic(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z\s\-]+", value):
            raise ValueError(
                "Name must contain only alphabetic characters, spaces, or hyphens."
            )
        return value

    @field_validator("password")
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit.")
        return value
