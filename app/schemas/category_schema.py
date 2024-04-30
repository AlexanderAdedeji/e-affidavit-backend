
from pydantic import  BaseModel


class Category(BaseModel):
    name:str


class CategoryInResponse(Category):
    id:str



class CategoryCreate(Category):
    created_by_id:str
    