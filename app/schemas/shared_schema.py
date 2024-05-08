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
    is_active:Optional[bool] = None
    





class DateRange(BaseModel):
    from_date: Optional[str] = ""
    to_date: Optional[str] = ""
