from pydantic import BaseModel, constr, field_validator


class UserTypeBase(BaseModel):
    name: constr(min_length=3, max_length=100)

    @field_validator("name", mode="before")
    def trim_name(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Name must be a string")
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Name must not be empty or whitespace")
        return trimmed

    class Config:
        orm_mode = True
        schema_extra = {"example": {"name": "Admin"}}


class UserTypeCreate(UserTypeBase):
    pass


class UserTypeUpdate(UserTypeBase):
    pass


class UserTypeInDB(UserTypeBase):
    id: str

    class Config:
        orm_mode = True
        schema_extra = {"example": {"id": "user_type_id_123", "name": "Admin"}}
