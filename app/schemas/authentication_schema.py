from typing import Optional 
import re
from pydantic import BaseModel,EmailStr, constr, validator


class ChangePassword(BaseModel):
    old_password: constr(min_length=8,max_length=128)
    new_password: constr(min_length=8,max_length=128)

    @validator("new_password")
    def new_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("New password must contain at least one letter and one digit.")
        return value
class UserUpdate(BaseModel):
    first_name: Optional[constr(min_length=1, max_length=50)]
    last_name: Optional[constr(min_length=1, max_length=50)]
    address: Optional[str] = None
    phone: Optional[constr(pattern=r'^\+?[1-9]\d{1,14}$')] = None
    password: Optional[constr(min_length=8, max_length=128)] = None

    @validator("first_name", "last_name")
    def names_must_be_alphabetic(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z\s\-]+", value):
            raise ValueError("Name must contain only alphabetic characters, spaces, or hyphens.")
        return value

    @validator("password")
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one digit.")
        return value





