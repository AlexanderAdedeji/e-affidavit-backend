import datetime
import logging
from typing import List, Optional
from fastapi import HTTPException
from pydantic import BaseModel

from app.core.errors.exceptions import ServerException


class Field(BaseModel):
    id:str
    name: str
    type: str
    required: bool


class TemplateContent(BaseModel):
    fields: List[Field]
    template_data: Optional[List[dict]]


class TemplateInResponse(BaseModel):
    id: str
    name: str
    price: int
    description: str
    content: TemplateContent
    category: str


class TemplateBase(TemplateInResponse):

    is_disabled: bool
    created_by_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        arbitrary_types_allowed = True


class TemplateCreateForm(BaseModel):
    name: str
    content: TemplateContent
    price: int
    description: str
    category: str


class TemplateCreate(TemplateCreateForm):
    created_by_id: str
    created_at: datetime = datetime.datetime.now(datetime.timezone.utc)

    class Config:
        arbitrary_types_allowed = True


class DocumentBase(BaseModel):
    name: str
    template_id: str
    date: str
    id: str
    content: TemplateContent
    user_id: str
    commissioner_id: int
    court_id: int


def safe_parse_datetime(datetime_string):
    try:
        return datetime.fromisoformat(datetime_string)
    except (TypeError, ValueError):
        return None


def template_individual_serializer(data) -> dict:
    try:
        # Convert timestamps to datetime objects
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        # if created_at:
        #     created_at = datetime.fromisoformat(created_at)
        # if updated_at:
        #     updated_at = datetime.fromisoformat(updated_at)

        # Serialize TemplateContent
        content_data = data.get("content", {})
        template_content = {
            "fields": [
                Field(**field).dict() for field in content_data.get("fields", [])
            ],
            "template_data": content_data.get("template_data", []),
        }

        # Complete serialization
        return {
            "id": str(data["_id"]),
            "name": data.get("name", ""),
            "price": data.get("price", 0),
            "category": data.get("category", ""),
            "description": data.get("description", ""),
            "content": template_content,  # Updated to match TemplateContent structure
            "is_disabled": data.get("is_disabled", False),
            "created_at": created_at,
            "updated_at": updated_at,
            "created_by_id": data.get("created_by_id", ""),
        }
    except KeyError as e:
        logging.error(f"Missing key in template data: {e}")
        raise


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


def template_list_serialiser(templates) -> list:
    return [template_individual_serializer(template) for template in templates]


def document_list_serialiser(documents) -> list:
    return [document_individual_serialiser(document) for document in documents]
