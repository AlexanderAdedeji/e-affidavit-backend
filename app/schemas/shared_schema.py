##this was created to remove circular import errors

from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.schemas.user_type_schema import UserTypeInDB

class SlimUserInResponse(BaseModel):
    id: str
    email: EmailStr

class UsersWithSharedType(BaseModel):
    users: List[SlimUserInResponse]
    user_type: Optional[UserTypeInDB]
