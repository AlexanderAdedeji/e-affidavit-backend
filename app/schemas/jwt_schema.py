from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class JWTUser(BaseModel):
    id: str


class JWTEMAIL(BaseModel):
    email: EmailStr


class JWTInvite(JWTUser):
    pass


class JWTMeta(BaseModel):
    exp: datetime
    sub: str

    @field_validator("exp")
    def check_expiration(cls, v: datetime) -> datetime:

        if v < datetime.utcnow():
            raise ValueError("Expiration time (exp) must be in the future")
        return v

    class Config:

        from_attributes = True
