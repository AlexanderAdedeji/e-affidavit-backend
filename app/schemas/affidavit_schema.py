import datetime
import logging
from typing import List
from fastapi import HTTPException
from pydantic import BaseModel

from app.core.errors.exceptions import ServerException


class Field(BaseModel):
    name: str
    feield_type: str
    required: bool


class TemplateBase(BaseModel):
    id: str
    name: str
    price: int
    description: str
    category: str
    fields: List[Field]
    template_data: list
    is_disabled: bool
    created_by_id: str
    created_at: datetime 
    updated_at: datetime
    class Config:
        arbitrary_types_allowed = True


class TemplateCreateForm(BaseModel):
    name:str
    fields:List[Field]
    price:int
    description:str
    category:str

class TemplateCreate(TemplateCreateForm):
    created_by_id:str
    created_at:datetime = datetime.datetime.now(datetime.timezone.utc)
    class Config:
        arbitrary_types_allowed = True


class DocumentBase(BaseModel):
    name: str
    template_id: str
    date: str
    document: dict
    id: str
    template_id: str
    document: list
    user_id: str
    commissioner_id: int
    court_id: int


def template_individual_serialiser(data) -> dict:
    try:
        return {
            "id": str(data["_id"]),
            "name": data.get("name", ""),
            "price": data.get("price", 0),
            "category":data.get("category",""),
            "description":data.get("description", ""),
            "is_disabled":data.get("is_disabled", False),
            "fields": [Field(**field).dict() for field in data.get('fields',[])],
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
            "created_by_id":data.get("created_by_id",""),
            "content": data.get("content", ""),
        }
    except KeyError as e:
        logging.error(f"Missing key in template data: {e}")
        raise ServerException()


def document_individual_serialiser(data) -> dict:
    try:
        return {
            "id": str(data["_id"]),
            "name": data.get("name", ""),
            "date": data.get("date", ""),
            "document": data.get("document", {}),
            "template_id": str(data.get("templateId", "")),
        }
    except KeyError as e:
        logging.error(f"Missing key in document data: {e}")
        return {}


def template_list_serialiser(data) -> list:
    return [template_individual_serialiser(item) for item in data]


def document_list_serialiser(data) -> list:
    return [document_individual_serialiser(item) for item in data]
