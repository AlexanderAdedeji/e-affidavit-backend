from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field, conint
from pydantic.generics import GenericModel

DataT = TypeVar("DataT")

class PaginationRequest(BaseModel):
    page: conint(ge=1) = Field(1, description="Current page number") # type: ignore
    per_page: conint(ge=1, le=100) = Field(10, description="Number of items per page") # type: ignore

class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total_count: int
    total_pages: int

class PaginatedResponse(GenericModel, Generic[DataT]):
    data: DataT
    meta: PaginationMeta



