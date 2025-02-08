import datetime
from typing import List

from pydantic import BaseModel, constr, field_validator

from app.schemas.shared_schema import SlimUserInResponse


class Category(BaseModel):
    name: constr(min_length=1, max_length=255)

    @field_validator("name")
    def name_must_be_trimmed(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Category name must not be empty or whitespace only.")
        return trimmed

    class Config:
        orm_mode = True


class CategoryInResponse(Category):
    id: str


class CategoryCreate(Category):
    created_by_id: str


class FullCategoryInResponse(CategoryInResponse):
    date_created: datetime.datetime
    created_by: SlimUserInResponse
    templates: List[dict] = []
