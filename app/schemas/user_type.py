from pydantic import BaseModel




class UserType(BaseModel):
    name: str


class UserTypeCreate(UserType):
    pass


class UserTypeUpdate(UserType):
    pass


class UserTypeInDB(UserType):
    id: int



