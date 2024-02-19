from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class JWTUser(BaseModel):
    id: str

class JWTEMAIL(BaseModel):
    email:EmailStr


class JWTInvite(JWTUser):
    pass

class JWTMeta(BaseModel):
    exp: datetime
    sub: str