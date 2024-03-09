from datetime import datetime
import logging
from typing import List
from uuid import uuid4

from loguru import logger
from app.api.dependencies.db import get_db
from app.models.user_model import User
from commonLib.response.response_schema import GenericResponse, create_response
import namegenerator
from sqlalchemy.orm import Session
from bson import ObjectId
from app.api.dependencies.authentication import (
    admin_permission_dependency,
    get_currently_authenticated_user,
)
from fastapi import Depends, HTTPException, APIRouter, status
from app.schemas.affidavit_schema import (
    DocumentBase,
    TemplateBase,
    TemplateCreate,
    TemplateCreateForm,
    document_individual_serialiser,
    document_list_serialiser,
    template_individual_serializer,
    template_list_serialiser,
)
from app.database.sessions.mongo_client import template_collection, document_collection


router = APIRouter()


@router.post(
    "/create_template",
    dependencies=[Depends(admin_permission_dependency)],
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponse[TemplateBase],
)
async def create_template(
    template_in: TemplateCreateForm,
    current_user: User = Depends(get_currently_authenticated_user),
):
    template_dict = template_in.dict()
    existing_template = await template_collection.find_one(
        {"name": template_dict["name"]}
    )
    if existing_template:

        raise HTTPException(
            status_code=400, detail="Template with the given name already exists"
        )
    template_dict = TemplateCreate(
        **template_dict, created_by_id=current_user.id
    ).dict()

    result = await template_collection.insert_one(template_dict)
    if not result.acknowledged:
        logger.error("Failed to insert template")
        raise HTTPException(status_code=500, detail="Failed to create template")

    new_template = await template_collection.find_one({"_id": result.inserted_id})
    return create_response(
        status_code=status.HTTP_201_CREATED,
        message=f"{new_template['name']} template Created Successfully",
        data=template_individual_serializer(new_template),
    )


@router.patch(
    "/update_template/{template_id}",
    # dependencies=[Depends(admin_permission_dependency)],
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[TemplateBase],
)
async def update_template(
    template_in: TemplateBase,
    # current_user: User = Depends(get_currently_authenticated_user),
):
    template_dict = {**template_in.dict(), "updated_at": datetime.utcnow()}
    existing_template = await template_collection.find_one(
        {"_id": template_dict["_id"]}
    )
    if not existing_template:

        raise HTTPException(
            status_code=400, detail="Template with the given name already exists"
        )
    # If a template with the same name exists, update it
    update_result = await template_collection.update_one(
        {"_id": existing_template["_id"]}, {"$set": template_dict}
    )
    if not update_result.modified_count:
        logger.error("Failed to update template")
        raise HTTPException(status_code=500, detail="Failed to update template")

    updated_template = await template_collection.find_one(
        {"_id": existing_template["_id"]}
    )
    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{updated_template['name']} template updated successfully",
        data=template_individual_serializer(updated_template),
    )


@router.get(
    "/get_templates",
    dependencies=[Depends(admin_permission_dependency)],
    response_model=GenericResponse[List[TemplateBase]],
)
async def get_templates():
    try:
        templates = await template_collection.find().to_list(
            length=100
        ) 
        if not templates:
            logger.info("No templates found")
            return create_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No templates found",
                data=[],
            )

        return create_response(
            status_code=status.HTTP_200_OK,
            message="Templates retrieved successfully",
            data=template_list_serialiser(templates),
        )

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
    template_obj = template_individual_serializer(template_obj)
    return template_obj


@router.get("/get_documents")
async def get_documents():
    try:
        documents = await document_collection.find().to_list(
            length=100
        )  # Set a reasonable limit
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

    template = await get_single_template(
        document_obj["templateId"]
    )  # Ensure this is correctly handled
    return {
        "name": document_obj["name"],
        "template": {"content": template["content"], "id": document_obj["templateId"]},
        "documentFields": document_obj["documentFields"],
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

    return template_individual_serializer(template_obj)


@router.post("/create_template_category")
def create_category(name: str, db: Session = Depends(get_db)):
    return ""


@router.get("/get_all_templates_category")
def get_all_category(db: Session = Depends(get_db)):
    return []


@router.get("/categories/{category_id}/templates/")
def get_templates_by_category(category: str, db: Session = Depends(get_db)):
    return []


@router.get("/templates/{template_id}/documents")
def get_documents_by_templates(template_id: str, db: Session = Depends(get_db)):
    return []


@router.get("/get_attested_affidavit_counts_by_court")
def get_attested_affidavit_counts_by_court(
    month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    return {"hello": "World"}
