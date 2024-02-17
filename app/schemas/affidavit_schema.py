import datetime
import logging
from pydantic import BaseModel


class TemplateBase(BaseModel):
    name: str

    price: str
    date: str
    content: str


class DocumentBase(BaseModel):
    name: str
    template_id: str
    date: str
    document: dict



def template_individual_serialiser(data) -> dict:
    try:
        return {
            "id": str(data["_id"]),
            "name": data.get("name", ""),
            "price": data.get("price", 0),
            "content": data.get("content", ""),
        }
    except KeyError as e:
        logging.error(f"Missing key in template data: {e}")
        return {}

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
