from pydantic import BaseModel




class UserTypeBase(BaseModel):
    name: str


class UserTypeCreate(UserTypeBase):
    pass


class UserTypeUpdate(UserTypeBase):
    pass


class UserTypeInDB(UserTypeBase):
    id: str



