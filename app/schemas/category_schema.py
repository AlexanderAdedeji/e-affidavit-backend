import datetime
from app.schemas.shared_schema import SlimUserInResponse
from pydantic import BaseModel

class Category(BaseModel):
    name: str


class CategoryInResponse(Category):
    id: str


class CategoryCreate(CategoryInResponse):
    created_by_id: str


class FullCategoryInResponse(CategoryInResponse):
    date_created:datetime.datetime
    created_by:SlimUserInResponse
    templates: list