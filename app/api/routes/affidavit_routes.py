import logging

from loguru import logger
from app.api.dependencies.db import get_db
import namegenerator
from sqlalchemy.orm import Session
from bson import ObjectId
from app.api.dependencies.authentication import admin_permission_dependency
from fastapi import Depends, HTTPException, APIRouter
from app.schemas.affidavit_schema import DocumentBase, TemplateBase, document_individual_serialiser, document_list_serialiser, template_individual_serialiser, template_list_serialiser
from app.database.sessions.mongo_client import template_collection, document_collection


router = APIRouter()
@router.get("/get_templates")
async def get_templates():
    try:
        templates = await template_collection.find().to_list(length=100)  # Set a reasonable limit
        if not templates:
            logger.info("No templates found")
            return []
        return template_list_serialiser(templates)
    except Exception as e:
        logger.error(f"Error fetching templates: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching templates")



@router.get("/get_single_template/{template_id}")
async def get_single_template(template_id: str):
    try:
        # Convert the string ID to ObjectId
        object_id = ObjectId(template_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ID format: {template_id}")

    # Log the ObjectId
    logging.info(f"Fetching template with ID: {object_id}")

    template_obj = await template_collection.find_one({"_id": object_id})

    # Log the result of the query
    if template_obj:
        logging.info(f"Found template: {template_obj}")
    else:
        logging.info("No template found")

    if not template_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Template with ID {template_id} does not exist",
        )

    # Assuming individual_serialiser is a valid function
    template_obj = template_individual_serialiser(template_obj)
    return template_obj


@router.get("/get_documents")
async def get_documents():
    try:
        documents = await document_collection.find().to_list(length=100)  # Set a reasonable limit
        if not documents:
            logger.info("No documents found")
            return []
        return document_list_serialiser(documents)
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching documents")



@router.get("/get_single_document/{document_id}")
async def get_single_document(document_id: str):
    try:
        object_id = ObjectId(document_id)
    except Exception as e:
        logger.error(f"Invalid ID format for document: {document_id} - {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid document ID format")
    
    document_obj = await document_collection.find_one({"_id": object_id})
    if not document_obj:
        logger.info(f"No document found with ID: {object_id}")
        raise HTTPException(status_code=404, detail="Document not found")

    template = await get_single_template(document_obj['templateId'])  # Ensure this is correctly handled
    return {
        "name": document_obj['name'],
        "template": {"content": template['content'], "id": document_obj['templateId']},
        "documentFields": document_obj['documentFields']
    }



@router.post("/create_document")
async def create_document(document_in: DocumentBase):
    document_dict = document_in.dict()
    document_dict["name"] = namegenerator.gen()

    try:
        result = await document_collection.insert_one(document_dict)
        if not result.acknowledged:
            logger.error("Failed to insert document")
            raise HTTPException(status_code=500, detail="Failed to create document")
        
        new_document = await document_collection.find_one({"_id": result.inserted_id})
        return document_individual_serialiser(new_document)
    except Exception as e:
        logger.error(f"Error creating document: {str(e)}")
        raise HTTPException(status_code=500, detail="Error creating document")

@router.get("/get_single_template/{template_id}")
async def get_single_template(template_id: str):
    try:
        object_id = ObjectId(template_id)
    except Exception as e:
        logger.error(f"Invalid ID format: {template_id} - {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid ID format")

    template_obj = await template_collection.find_one({"_id": object_id})
    if not template_obj:
        logger.info(f"No template found with ID: {object_id}")
        raise HTTPException(status_code=404, detail="Template not found")

    return template_individual_serialiser(template_obj)

@router.post("/create_template", dependencies=[Depends(admin_permission_dependency)])
async def create_template(template_in: TemplateBase):
    template_dict = template_in.dict()
    template_dict["name"] = namegenerator.gen()
    
    result = await template_collection.insert_one(template_dict)
    if not result.acknowledged:
        logger.error("Failed to insert template")
        raise HTTPException(status_code=500, detail="Failed to create template")

    new_template = await template_collection.find_one({"_id": result.inserted_id})
    return template_individual_serialiser(new_template)


@router.post("/create_template_category")
def create_category(name: str, db:Session = Depends(get_db)):
    return ""

@router.get("/get_all_templates_category")
def  get_all_category(db: Session = Depends(get_db)):
    return []


@router.get("/categories/{category_id}/templates/")
def get_templates_by_category(category: str, db: Session = Depends(get_db)):
    return []

@router.get("/templates/{template_id}/documents")
def get_documents_by_templates(template_id: str, db: Session = Depends(get_db)):
    return []

