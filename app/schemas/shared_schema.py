##this was created to remove circular import errors
from fastapi import FastAPI, Query, HTTPException

from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.schemas.user_type_schema import UserTypeInDB


class SlimUserInResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    


class UsersWithSharedType(BaseModel):
    users: List[SlimUserInResponse]
    user_type: Optional[UserTypeInDB]


class DateRange(BaseModel):
    from_date: Optional[str] = (
        Query(None, description="Start date in YYYY-MM-DD format"),
    )
    to_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format")
