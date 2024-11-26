import datetime
from typing import List
from app.schemas.shared_schema import SlimUserInResponse
from pydantic import BaseModel,constr

class Category(BaseModel):
    name: constr(min_length=1, max_length=255)

    class Config:
        orm_mode = True


class CategoryInResponse(Category):
    id: str


class CategoryCreate(Category):
    created_by_id: str


class FullCategoryInResponse(CategoryInResponse):
    date_created: datetime.datetime
    created_by: SlimUserInResponse
    templates: List[str] = []