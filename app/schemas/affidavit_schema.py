import datetime
import logging
from typing import List, Optional
from fastapi import HTTPException
from pydantic import BaseModel
from bson import ObjectId

from app.core.errors.exceptions import ServerException


class Field(BaseModel):
    id: str
    name: str
    type: str
    required: bool
    label:str


class TemplateContent(BaseModel):
    fields: Optional[List[Field]]
    template_data: Optional[List[dict]]


class SlimTemplateInResponse(BaseModel):
    id: str
    name: str
    price: int
    description: str
    category: str


class TemplateInResponse(SlimTemplateInResponse):

    content: TemplateContent


class TemplateBase(TemplateInResponse):

    is_disabled:Optional[ bool] = False  # Is the template disabled?
    created_by_id: str
    created_at: datetime
    updated_at: Optional[datetime.datetime] = None

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
    id: str
    user_id: str
    commissioner_id: str
    is_attested: bool
    attestation_date: Optional[datetime.datetime]
    status: str
    amount_paid: int
    payment_ref: str
    created_at: str
    updated_at: str


class UpdateDocument(BaseModel):
    created_by_id: str
    commissioner_id: Optional[str] = None
    attestation_date: Optional[datetime.datetime] = None
    status: Optional[str] = None
    amount_paid: Optional[int] = None
    payment_ref: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None
    template_id: str
    court_id: Optional[str] = None
    document_data: TemplateContent
    qr_code: Optional[str] = None
    is_attested: Optional[bool] = None
    name: str


class AttestDocument(BaseModel):
    document_data: TemplateContent


class DocumentCreateForm(BaseModel):
    document_data: TemplateContent
    template_id: str
    court_id: str


class SlimDocumentInResponse(BaseModel):
    id: str
    name: str
    price: Optional[int] = None
    attestation_date: Optional[str] = None
    created_at: datetime.datetime
    status: str


class DocumentPayment(BaseModel):

    payment_ref: str
    amount_paid: int
    # document_data: TemplateContent


class LastestAffidavits(SlimDocumentInResponse):
    court: str
    template: str


class DocumentCreate(DocumentCreateForm):
    created_by_id: str
    name: str
    qr_code: str
    created_at: datetime = datetime.datetime.now(datetime.timezone.utc)
    status: str

    class Config:
        arbitrary_types_allowed = True


def template_individual_serializer(data) -> dict:
    try:
        created_at = data.get("created_at", "")
        updated_at = data.get(
            "updated_at",
        )
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
        raise HTTPException(
            status_code=403, detail=f"Missing key in template data: {e}"
        )


def document_individual_serializer(data) -> dict:
    created_at = data.get("created_at")
    updated_at = data.get("updated_at")
    attestation_date = data.get("attestation_date")
    try:
        return {
            "id": str(data["_id"]),
            "name": data.get("name", ""),
            "date": data.get("date", ""),
            "document": data.get("document", {}),
            "template_id": str(data.get("templateId", "")),
            "created_by_id": data.get("created_by_id", ""),
            "created_at": created_at,
            "updated_at": updated_at,
            "commissioner_id": data.get("commissioner_id", ""),
            "is_attested": bool(data.get("isAttested", False)),
            "attestation_date": attestation_date,
            "status": data.get("status"),
            "payment_ref": data.get("payment_ref", ""),
            "qr_code: str": data.get("qr_code: str", ""),
        }
    except KeyError as e:
        logging.error(f"Missing key in document data: {e}")
        return {}







def serialize_mongo_document(document):
    if isinstance(document, list):
        # If the document is a list, apply serialization to each item in the list.
        return [serialize_mongo_document(doc) for doc in document]

    if not isinstance(document, dict):
        # If the document is not a dictionary, return it as is.
        return document

    serialized_document = {}
    for key, value in document.items():
        new_key = "id" if key == "_id" else key  # Convert '_id' to 'id'

        if isinstance(value, ObjectId):
            # Convert ObjectId to string
            serialized_document[new_key] = str(value)
        elif isinstance(value, (dict, list)):
            # Recursively serialize dictionaries or lists
            serialized_document[new_key] = serialize_mongo_document(value)
        else:
            # For all other types, assign the value directly.
            serialized_document[new_key] = value

    return serialized_document


def template_list_serialiser(templates) -> list:
    return [template_individual_serializer(template) for template in templates]


def document_list_serialiser(documents) -> list:
    return [document_individual_serializer(document) for document in documents]
