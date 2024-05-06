from typing import Optional 
from pydantic import BaseModel,EmailStr


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


class UserUpdate(BaseModel):

    first_name: Optional[str]
    last_name: Optional[str]
    address: Optional[str]=None
    phone: Optional[str]=None
    password: Optional[str] = None
