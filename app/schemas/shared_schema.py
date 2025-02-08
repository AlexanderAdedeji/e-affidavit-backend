from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from app.schemas.user_type_schema import UserTypeInDB

class SlimUserInResponse(BaseModel):
    id: str = Field(..., description="Unique identifier for the user")
    first_name: str = Field(..., min_length=1, max_length=50, description="User's first name")
    last_name: str = Field(..., min_length=1, max_length=50, description="User's last name")
    email: EmailStr = Field(..., description="User's email address")
    is_active: Optional[bool] = Field(None, description="Indicates if the user is active")
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "user123",
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "is_active": True
            }
        }

class DateRange(BaseModel):
    from_date: Optional[str] = Field(
        "", 
        description="Start date in ISO format (YYYY-MM-DD)"
    )
    to_date: Optional[str] = Field(
        "", 
        description="End date in ISO format (YYYY-MM-DD)"
    )
    
    @validator('from_date', 'to_date', pre=True, always=True)
    def validate_date_format(cls, v):
        if v == "":
            return v
        try:
            # Attempt to parse the date; adjust the format if necessary.
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in ISO format (YYYY-MM-DD)")
        return v

    class Config:
        schema_extra = {
            "example": {
                "from_date": "2023-01-01",
                "to_date": "2023-12-31"
            }
        }
