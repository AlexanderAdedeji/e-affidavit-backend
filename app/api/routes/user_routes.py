
import datetime
import uuid
from typing import Any, Dict, List

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks,  Depends, HTTPException, status , Query
from loguru import logger
from postmarker import core
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# Import dependencies
from app.api.dependencies.authentication import (
    authenticated_user_dependencies,
    get_currently_authenticated_user,
)
from app.api.dependencies.db import get_db
from app.api.routes.payment_routes import verify_payment
from app.core.errors.exceptions import AlreadyExistsException, DoesNotExistException, UnauthorizedEndpointException
from app.core.services.email import email_service
from app.core.services.utils.utils import (
    extract_preview_text_from_document,
    generate_document_name,
    generate_qr_code_base64,
    is_valid_objectid,
)
from app.core.settings.configurations import settings
from app.database.sessions.mongo_client import document_collection, template_collection
from app.models.court_system_models import Court, Jurisdiction
from app.models.user_model import User
from app.repositories.category_repo import category_repo
from app.repositories.court_system_repo import court_repo, state_repo
from app.repositories.user_repo import user_repo
from app.repositories.user_type_repo import user_type_repo
from app.schemas.affidavit_schema import (
    DocumentCreate,
    DocumentCreateForm,
    DocumentPayment,
    DocumentSearchResponse,
    LastestAffidavits,
    ReceiptInResponse,
    SearchResult,
    SlimDocumentInResponse,
    TemplateBase,
    TemplateContent,
    TemplateInResponse,
    UpdateDocument,
    serialize_mongo_document,
    template_list_serialiser,
)
from app.schemas.category_schema import CategoryInResponse, FullCategoryInResponse
from app.schemas.court_system_schema import CourtSystemInDB
from app.schemas.email_schema import UserCreationTemplateVariables
from app.schemas.payment_schema import PaymentCreate
from app.schemas.shared_schema import SlimUserInResponse
from app.schemas.stats_schema import PublicDashboardStat
from app.schemas.user_schema import UserCreate, UserCreateForm, UserInResponse
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import GenericResponse, create_response

router = APIRouter()

# Constants for frontend URLs and templates
PUBLIC_FRONTEND_BASE_URL = settings.PUBLIC_FRONTEND_BASE_URL
VERIFY_EMAIL_LINK = settings.VERIFY_EMAIL_LINK
CREATE_ACCOUNT_TEMPLATE_ID = settings.CREATE_ACCOUNT_TEMPLATE_ID

# ─── HELPER FUNCTIONS ─────────────────────────────────────────────

def validate_objectid(document_id: str) -> ObjectId:
    """Validate and return an ObjectId from a string; raise an HTTPException if invalid."""
    if not is_valid_objectid(document_id):
        logger.error(f"Invalid ObjectId format: {document_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID format"
        )
    return ObjectId(document_id)

# ─── ENDPOINTS ───────────────────────────────────────────────────

@router.get("/search")
async def search_documents(
    query: str, current_user: User = Depends(get_currently_authenticated_user)
):
    """
    Search for documents by name for the current user.
    """
    if not query:
        logger.warning("Empty search query provided")
        raise HTTPException(status_code=400, detail="Query parameter is required")
    try:
        cursor = document_collection.find({
            "name": {"$regex": f"^{query}", "$options": "i"},
            "created_by_id": current_user.id,
        })
        documents = await cursor.to_list(length=100)
        result = {"documents": serialize_mongo_document(documents)}
        logger.info(f"Search query '{query}' executed successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Search retrieved successfully",
            data=result,
        )
    except Exception as e:
        logger.error("Error during document search", exc_info=True)
        raise HTTPException(status_code=500, detail="Error searching for document")


@router.get("/get_dashboard_stats")
async def get_dashboard_stats(current_user: User = Depends(get_currently_authenticated_user)):
    """
    Retrieve dashboard statistics for the current user.
    """
    try:
        total_saved = await document_collection.count_documents({
            "created_by_id": current_user.id,
            "status": "SAVED",
            "is_archived": False
        })
        total_paid = await document_collection.count_documents({
            "created_by_id": current_user.id,
            "status": "PAID",
            "is_archived": False
        })
        total_attested = await document_collection.count_documents({
            "created_by_id": current_user.id,
            "status": "ATTESTED",
            "is_archived": False
        })
        total_documents = await document_collection.count_documents({
            "created_by_id": current_user.id,
            "is_archived": False
        })
        logger.info("Dashboard stats retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Dashboard stats retrieved successfully",
            data=PublicDashboardStat(
                total_saved=total_saved,
                total_paid=total_paid,
                total_attested=total_attested,
                total_documents=total_documents,
            ),
        )
    except Exception as e:
        logger.error("Error retrieving dashboard stats", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving dashboard stats")


@router.post("/user",status_code=status.HTTP_201_CREATED,
              response_model=GenericResponse[UserInResponse]
              )
def create_user(
    user_in: UserCreateForm,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    

    """
    Create a new user (public account) and send a verification email.
    """
    try:
        if user_repo.get_by_email(email=user_in.email, db=db):
            logger.warning(f"User with email {user_in.email} already exists")
            raise AlreadyExistsException(
                entity_name=f"User with email {user_in.email} already exists"
            )
        user_type = user_type_repo.get_by_name(name=settings.PUBLIC_USER_TYPE, db=db)
        if not user_type:
            logger.error("User type not found for public user")
            raise DoesNotExistException(entity_name="User type not found.")
        user_data = UserCreate(**user_in.dict(), user_type_id=user_type.id)
        new_user = user_repo.create(obj_in=user_data, db=db)
        verify_token = user_repo.create_verification_token(email=new_user.email, db=db)
        verification_link = f"{PUBLIC_FRONTEND_BASE_URL}{VERIFY_EMAIL_LINK}{verify_token}"
        template_dict = UserCreationTemplateVariables(
            name=f"{new_user.first_name} {new_user.last_name}",
            action_url=verification_link,
        ).dict()
        email_service.send_email_with_template(
            db=db,
            template_id=CREATE_ACCOUNT_TEMPLATE_ID,
            template_dict=template_dict,
            recipient=new_user.email,
            background_tasks=background_tasks,
        )
        logger.info(f"User {new_user.email} created successfully")
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message="Account created successfully",
            data=UserInResponse(
                id=new_user.id,
                first_name=new_user.first_name,
                last_name=new_user.last_name,
                email=new_user.email,
                is_active=new_user.is_active,
                user_type=UserTypeInDB(name=user_type.name, id=user_type.id),
            ),
        )
    except Exception as e:
        logger.error(f"Error creating user: %s {str(e)}")
        raise HTTPException(status_code=500, detail="User creation failed")


@router.get("/me")
def retrieve_current_user(
    current_user: User = Depends(get_currently_authenticated_user),
) -> UserInResponse:
    """
    Retrieve the current user's profile.
    """
    logger.info(f"Retrieving profile for user {current_user.email}")
    return UserInResponse(
        id=current_user.id,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email,
        is_active=current_user.is_active,
        user_type=UserTypeInDB(
            id=current_user.user_type.id,
            name=current_user.user_type.name,
        ),
        verify_token="",
    )



@router.get("/my_documents", dependencies=[Depends(authenticated_user_dependencies)])
async def get_my_documents(
    current_user: User = Depends(get_currently_authenticated_user),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100)  # Now defaulting to 25 documents per page
):
    """
    Retrieve non-archived documents for the current user using pagination.
    """
    # Ensure index exists to optimize the query
    await document_collection.create_index([
        ("created_by_id", 1),
        ("is_archived", 1),
        ("created_at", -1)
    ])
    
    skip = (page - 1) * limit
    docs_cursor = document_collection.find(
        {"created_by_id": current_user.id, "is_archived": False},
        {"name": 1, "preview_text": 1, "created_at": 1, "status": 1}
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    documents = await docs_cursor.to_list(length=limit)
    total_count = await document_collection.count_documents({
        "created_by_id": current_user.id,
        "is_archived": False
    })
    
    pagination_meta = {
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit  # Ceiling division
    }
    
    logger.info(f"{len(documents)} documents retrieved for user {current_user.email} (Page {page})")
    
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Documents retrieved successfully with pagination",
        data=serialize_mongo_document(documents),
        pagination=pagination_meta
    )

# @router.get("/my_documents", dependencies=[Depends(authenticated_user_dependencies)])
# async def get_documents_index(current_user: User = Depends(get_currently_authenticated_user)):
#     """
#     Retrieve non-archived documents for the current user using an indexed query.
#     This solution ensures a compound index is used so that sorting by 'created_at'
#     does not exceed MongoDB's in-memory sort limit.
#     """
#     await document_collection.create_index([
#         ("created_by_id", 1),
#         ("is_archived", 1),
#         ("created_at", -1)
#     ])
    
#     # Use a simple find query that leverages the index.
#     docs_cursor = document_collection.find(
#     {
#         "created_by_id": current_user.id,
#         "is_archived": False
#     },
#     {
#         "name": 1,
#         "preview_text": 1,
#         "created_at": 1,
#         "status": 1
#     }
# ).sort("created_at", -1)
    
#     documents = await docs_cursor.to_list(length=1000)
#     logger.info(f"{len(documents)} documents retrieved for user {current_user.email} using indexed query")
    
#     return create_response(
#         status_code=status.HTTP_200_OK,
#         message="Documents retrieved successfully using index",
#         data=serialize_mongo_document(documents)
#     )



@router.get("/get_archived_documents", dependencies=[Depends(authenticated_user_dependencies)])
async def get_archived_documents(current_user: User = Depends(get_currently_authenticated_user)):
    """
    Retrieve archived documents for the current user.
    """
    try:
        docs_cursor = document_collection.find({
            "created_by_id": current_user.id,
            "is_archived": True
        })
        documents = await docs_cursor.to_list(length=100)
        msg = "Archived documents retrieved successfully" if documents else "No Documents Found"
        logger.info(f"Archived documents retrieval: {msg}")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=msg,
            data=serialize_mongo_document(documents),
        )
    except Exception as e:
        logger.error("Error fetching archived documents", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching archived documents")


@router.get("/get_my_latest_affidavits", dependencies=[Depends(authenticated_user_dependencies)])
async def get_my_latest_affidavits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Retrieve the five most recent documents for the current user.
    """
    try:
        documents = (
    await document_collection.find(
        {"created_by_id": current_user.id, "is_archived": False},
        {"name": 1, "court_id": 1, "template_id": 1, "status": 1, "created_at": 1, "price": 1, "attestation_date": 1}
    )
    .sort("created_at", -1)
    .limit(5)
    .to_list(length=5)
)
        if not documents:
            logger.info("No documents found")
        enriched_docs = []
        for doc in serialize_mongo_document(documents):
            court = court_repo.get(db, id=doc.get("court_id"))
            template = await template_collection.find_one({"_id": ObjectId(doc.get("template_id", ""))})
            doc["court"] = court.name if court else "Unknown Court"
            doc["template"] = template.get("name", "Unknown Template") if template else "Unknown Template"
            enriched_docs.append(doc)
        logger.info("Latest affidavits retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Documents retrieved successfully",
            data=[
                LastestAffidavits(
                    name=d.get("name", ""),
                    court=d.get("court", ""),
                    template=d.get("template", ""),
                    id=d.get("id", ""),
                    status=d.get("status", ""),
                    created_at=d.get("created_at", ""),
                    price=d.get("price", 0),
                    attestation_date=str(d.get("attestation_date", "")),
                )
                for d in enriched_docs
            ],
        )
    except Exception as e:
        logger.error("Error fetching latest affidavits", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching documents")


@router.get("/get_document/{document_id}")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Retrieve a document by its ID for the current user.
    """
    try:
        oid = validate_objectid(document_id)
        document = await document_collection.find_one({"_id": oid, "created_by_id": current_user.id})
        if not document:
            logger.error(f"Document {document_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Document not found")
        logger.info(f"Document {document_id} retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{document.get('name')} retrieved successfully",
            data=serialize_mongo_document(document),
        )
    except Exception as e:
        logger.error("Error retrieving document", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving document")


@router.get("/get_receipt/{document_id}")
async def get_receipt(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Retrieve a receipt for a document.
    """
    try:
        oid = validate_objectid(document_id)
        document = await document_collection.find_one({"_id": oid, "created_by_id": current_user.id})
        if not document:
            logger.error(f"Document {document_id} not found for receipt retrieval")
            raise HTTPException(status_code=404, detail="Document not found")
        document = serialize_mongo_document(document)
        court = court_repo.get(db, id=document.get("court_id"))
        db_template = await template_collection.find_one({"_id": ObjectId(document.get("template_id", ""))})
        template = serialize_mongo_document(db_template) if db_template else {}
        logger.info(f"Receipt generated for document {document.get('name')}")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{document.get('name')} retrieved successfully",
            data=ReceiptInResponse(
                court_name=court.name if court else "Unknown Court",
                document_name=document.get("name", ""),
                template_name=template.get("name", "Unknown Template"),
                qr_code=document.get("qr_code", ""),
                payment_date=str(document.get("payment_date", "")),
            ),
        )
    except Exception as e:
        logger.error("Error retrieving receipt", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving receipt")


@router.get("/get_document_by_name")
async def get_document_by_name(document_name: str):
    """
    Retrieve a document by its name.
    """
    try:
        document = await document_collection.find_one({"name": document_name})
        if not document:
            logger.error(f"Document with name {document_name} not found")
            raise HTTPException(status_code=404, detail="Document not found")
        logger.info(f"Document {document_name} retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{document.get('name')} verified successfully",
            data=serialize_mongo_document(document),
        )
    except Exception as e:
        logger.error("Error retrieving document by name", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving document")


@router.get(
    "/get_templates",
    response_model=GenericResponse[List[TemplateInResponse]],
    dependencies=[Depends(authenticated_user_dependencies)],
)
async def get_templates():
    """
    Retrieve all active templates.
    """
    try:
        templates = await template_collection.find({"is_disabled": False}).to_list(length=100)
        if not templates:
            logger.info("No templates found")
            return create_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No templates found",
                data=[],
            )
        templates = serialize_mongo_document(templates)
        logger.info("Templates retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Templates retrieved successfully",
            data=[
                TemplateInResponse(
                    id=t.get("id"),
                    name=t.get("name"),
                    description=t.get("description"),
                    content=t.get("content"),
                    price=t.get("price"),
                    category_id=t.get("category_id"),
                )
                for t in templates
            ],
        )
    except Exception as e:
        logger.error("Error retrieving templates", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching templates")


@router.get(
    "/get_templates_by_category/{category_id}",
    response_model=GenericResponse[List[TemplateInResponse]],
    dependencies=[Depends(authenticated_user_dependencies)],
)
async def get_templates_by_category(category_id: str):
    """
    Retrieve all active templates for a given category.
    """
    try:
        templates = await template_collection.find({"is_disabled": False, "category_id": category_id}).to_list(length=100)
        if not templates:
            logger.info(f"No templates found for category {category_id}")
            return create_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No templates found",
                data=[],
            )
        templates = serialize_mongo_document(templates)
        logger.info(f"Templates for category {category_id} retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Templates retrieved successfully",
            data=[
                TemplateInResponse(
                    id=t.get("id"),
                    name=t.get("name"),
                    description=t.get("description"),
                    content=t.get("content"),
                    price=t.get("price"),
                    category_id=t.get("category_id"),
                )
                for t in templates
            ],
        )
    except Exception as e:
        logger.error("Error retrieving templates by category", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching templates by category")


@router.get(
    "/get_template/{template_id}",
    response_model=GenericResponse[TemplateInResponse],
    dependencies=[Depends(authenticated_user_dependencies)],
)
async def get_template_for_document_creation(template_id: str):
    """
    Retrieve a single template for document creation.
    """
    try:
        oid = validate_objectid(template_id)
        logger.info(f"Fetching template with ObjectId: {oid}")
        template_obj = await template_collection.find_one({"_id": oid})
        if template_obj.get("is_disabled"):
            logger.warning("Template is disabled")
            raise HTTPException(status_code=404, detail="Template is not available at the moment")
        if not template_obj:
            logger.error("Template not found")
            raise HTTPException(status_code=404, detail=f"Template with ID {template_id} does not exist")
        template_obj = serialize_mongo_document(template_obj)
        logger.info(f"Template {template_obj.get('name')} retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{template_obj.get('name')} retrieved successfully",
            data=TemplateInResponse(
                id=template_obj.get("id"),
                name=template_obj.get("name"),
                description=template_obj.get("description"),
                content=template_obj.get("content"),
                price=template_obj.get("price"),
                category_id=template_obj.get("category_id"),
            ),
        )
    except Exception as e:
        logger.error("Error retrieving template", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving template")


@router.delete("/delete_document/{document_id}")
async def delete_document(
    document_id: str, current_user: User = Depends(get_currently_authenticated_user)
):
    """
    Delete a document if it is in SAVED status.
    """
    try:
        oid = validate_objectid(document_id)
        document = await document_collection.find_one({"_id": oid})
        if not document:
            logger.error("Document not found for deletion")
            raise DoesNotExistException(entity_name="Document")
        if document.get("created_by_id") != current_user.id:
            logger.warning("Unauthorized deletion attempt")
            raise UnauthorizedEndpointException(detail="You are not authorised to delete this document")
        if document.get("status") != "SAVED":
            logger.warning("Attempt to delete non-SAVED document")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Only saved documents can be deleted, try archiving instead",
            )
        delete_result = await document_collection.delete_one({"_id": oid})
        if delete_result.deleted_count == 0:
            logger.error("Document deletion failed")
            raise HTTPException(status_code=404, detail="Document not found")
        logger.info(f"Document {document.get('name')} deleted successfully")
        return create_response(
            status_code=status.HTTP_204_NO_CONTENT,
            message=f"{document.get('name')} has been deleted successfully.",
        )
    except Exception as e:
        logger.error("Error deleting document", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting document")


@router.put("/archive_document/{document_id}")
async def toggle_archive_document(document_id: str, current_user: User = Depends(get_currently_authenticated_user)):
    """
    Toggle the archive status of a document.
    """
    try:
        oid = validate_objectid(document_id)
        document = await document_collection.find_one({"_id": oid})
        if not document:
            logger.error("Document not found for archiving")
            raise DoesNotExistException(entity_name="Document")
        if document.get("created_by_id") != current_user.id:
            logger.warning("Unauthorized archive attempt")
            raise UnauthorizedEndpointException(detail="You are not authorised to archive this document")
        new_status = not document.get("is_archived", False)
        message = f"{document.get('name')} has been {'restored' if not new_status else 'archived'} successfully"
        update_result = await document_collection.update_one(
            {"_id": oid}, {"$set": {"is_archived": new_status}}
        )
        if update_result.modified_count == 0:
            logger.error("Document archive toggle failed")
            raise HTTPException(status_code=404, detail="Document not found or no update made")
        logger.info(message)
        return create_response(
            status_code=status.HTTP_200_OK,
            message=message,
        )
    except Exception as e:
        logger.error("Error toggling archive status", exc_info=True)
        raise HTTPException(status_code=500, detail="Error toggling archive status")


@router.patch("/update_document/{document_id}")
async def update_document(
    document_id: str,
    document_in: UpdateDocument,
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Update a document's details.
    """
    try:
        oid = validate_objectid(document_id)
        document = await document_collection.find_one({"_id": oid, "created_by_id": current_user.id})
        if not document:
            logger.error("Document not found for update")
            raise HTTPException(status_code=404, detail="Document not found")
        update_data = document_in.dict(exclude_unset=True)
        if not update_data:
            logger.info("No changes detected for document update")
            return create_response(
                status_code=status.HTTP_200_OK,
                message="No changes detected.",
                data=None,
            )
        update_result = await document_collection.update_one(
            {"_id": oid}, {"$set": update_data}
        )
        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        if update_result.modified_count == 0:
            logger.info("No modifications applied to document")
            return create_response(
                status_code=status.HTTP_200_OK,
                message="No changes were made to the document.",
                data=None,
            )
        updated_document = await document_collection.find_one({"_id": oid})
        if not updated_document:
            raise HTTPException(status_code=404, detail="Document not found after update")
        logger.info(f"Document {updated_document.get('name')} updated successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{updated_document.get('name')} has been updated successfully",
            data=None,
        )
    except Exception as e:
        logger.error("Error updating document", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating document")


@router.put("/pay_for_document/{document_id}")
async def pay_for_document(
    document_id: str,
    document_in: DocumentPayment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Verify payment for a document and update its status accordingly.
    """
    try:
        payment_data = PaymentCreate(
            reference=document_in.payment_ref,
            document_id=document_id,
            user_id=current_user.id,
        )
        result = await verify_payment(data=payment_data, db=db)
        if result.get("status") == "success":
            now = datetime.datetime.now()
            update_data = document_in.dict(exclude_unset=True)
            update_data.update({
                "status": "PAID",
                "updated_at": now,
                "payment_date": now,
            })
            oid = validate_objectid(document_id)
            update_result = await document_collection.update_one({"_id": oid}, {"$set": update_data})
            if update_result.modified_count == 0:
                raise HTTPException(status_code=404, detail="Document not found or no update made.")
            updated_document = await document_collection.find_one({"_id": oid})
            if not updated_document:
                raise HTTPException(status_code=404, detail="Document not found after update.")
            logger.info(f"Document {updated_document.get('name')} paid successfully")
            return create_response(
                status_code=status.HTTP_200_OK,
                message=f"{updated_document.get('name')} has been paid for successfully",
                data=serialize_mongo_document(updated_document),
            )
        else:
            logger.warning("Payment verification failed")
            raise HTTPException(status_code=400, detail="Payment verification failed")
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error("Error during payment verification", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred during payment verification")


@router.get("/get_states", response_model=GenericResponse[List[CourtSystemInDB]])
def get_states(db: Session = Depends(get_db)):
    """
    Retrieve a list of all states.
    """
    try:
        states_list = state_repo.get_all(db)
        logger.info(f"{len(states_list)} states retrieved")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{len(states_list)} States Retrieved Successfully!",
            data=[CourtSystemInDB(id=state.id, name=state.name) for state in states_list],
        )
    except Exception as e:
        logger.error("Error retrieving states", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving states")


@router.get(
    "/get_jurisdictions_by_state/{state_id}",
    response_model=GenericResponse[List[CourtSystemInDB]],
)
def get_jurisdictions_by_states(state_id: str, db: Session = Depends(get_db)):
    """
    Retrieve all jurisdictions for a given state.
    """
    try:
        jurisdictions = db.query(Jurisdiction).filter(Jurisdiction.state_id == state_id).all()
        logger.info(f"{len(jurisdictions)} jurisdictions retrieved for state {state_id}")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{len(jurisdictions)} Jurisdictions Retrieved Successfully!",
            data=[CourtSystemInDB(id=jurisdiction.id, name=jurisdiction.name) for jurisdiction in jurisdictions],
        )
    except Exception as e:
        logger.error("Error retrieving jurisdictions", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving jurisdictions")


@router.get(
    "/get_courts_by_jursdiction/{jurisdiction_id}",
    response_model=GenericResponse[List[CourtSystemInDB]],
)
def get_courts_by_jurisdiction(jurisdiction_id: str, db: Session = Depends(get_db)):
    """
    Retrieve all courts for a given jurisdiction.
    """
    try:
        courts = db.query(Court).filter(Court.jurisdiction_id == jurisdiction_id).all()
        logger.info(f"{len(courts)} courts retrieved for jurisdiction {jurisdiction_id}")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{len(courts)} Courts Retrieved Successfully!",
            data=[CourtSystemInDB(id=court.id, name=court.name) for court in courts],
        )
    except Exception as e:
        logger.error("Error retrieving courts by jurisdiction", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving courts")


@router.post("/create_document")
async def create_document(
    document_in: DocumentCreateForm,
    current_user: User = Depends(get_currently_authenticated_user),
) -> Any:
    """
    Create a new document with a generated name and QR code.
    """
    try:
        document_name = generate_document_name()
        qr_url = f"{settings.VERIFY_DOCUMENT_URL}{document_name}"
        qr_code_base64 = generate_qr_code_base64(qr_url)
        document_dict = document_in.dict()
        # Add additional document metadata
        document_dict.update({
            "name": document_name,
            "preview_text": extract_preview_text_from_document(document_dict),
            "status": "SAVED",
            "qr_code": qr_code_base64,
            "created_by_id": current_user.id,
        })
        logger.info(f"Creating document with name: {document_name}")
        document_obj = DocumentCreate(**document_dict)
        result = await document_collection.insert_one(document_obj.dict())
        if not result.acknowledged:
            logger.error("Failed to insert document into MongoDB")
            raise HTTPException(status_code=500, detail="Failed to create document")
        new_document = await document_collection.find_one({"_id": result.inserted_id})
        if not new_document:
            logger.error("Document not found after insertion")
            raise HTTPException(status_code=404, detail="Document not found after creation")
        logger.info(f"Document {new_document.get('name')} created successfully")
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message=f"Document {new_document.get('name')} created successfully.",
            data=serialize_mongo_document(new_document),
        )
    except Exception as e:
        logger.error("Error creating document", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating document")


@router.get("/get_affidavit_categories")
async def get_categories(db: Session = Depends(get_db)):
    """
    Retrieve all affidavit categories with associated templates.
    """
    try:
        categories = category_repo.get_all(db)
        full_categories = []
        for category in categories:
            templates_cursor = template_collection.find({"category_id": category.id}).sort([("updated_at", -1), ("created_at", -1)])
            templates = await templates_cursor.to_list(length=1000)
            full_categories.append(
                FullCategoryInResponse(
                    name=category.name,
                    id=category.id,
                    created_by=SlimUserInResponse(
                        id=category.user.id,
                        first_name=category.user.first_name,
                        last_name=category.user.last_name,
                        email=category.user.email,
                    ),
                    date_created=category.CreatedAt,
                    templates=[serialize_mongo_document(t) for t in templates],
                )
            )
        logger.info("Affidavit categories retrieved successfully")
        return create_response(
            data=full_categories,
            status_code=status.HTTP_200_OK,
            message="Categories Retrieved Successfully",
        )
    except Exception as e:
        logger.error("Error retrieving affidavit categories", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving categories")




















# import datetime
# import uuid
# from typing import Any, Dict, List

# from bson import ObjectId
# from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, status, Request
# from loguru import logger
# from postmarker import core
# from sqlalchemy.exc import IntegrityError
# from sqlalchemy.orm import Session

# # Import dependencies and schemas
# from app.api.dependencies.authentication import (
#     authenticated_user_dependencies,
#     get_currently_authenticated_user,
# )
# from app.api.dependencies.db import get_db
# from app.api.routes.payment_routes import verify_payment
# from app.core.errors.exceptions import AlreadyExistsException, DoesNotExistException, UnauthorizedEndpointException
# from app.core.services.email import email_service
# from app.core.services.utils.utils import (
#     extract_preview_text_from_document,
#     generate_document_name,
#     generate_qr_code_base64,
#     is_valid_objectid,
# )
# from app.core.settings.configurations import settings
# from app.database.sessions.mongo_client import document_collection, template_collection
# from app.models.court_system_models import Court, Jurisdiction
# from app.models.user_model import User
# from app.repositories.category_repo import category_repo
# from app.repositories.court_system_repo import court_repo, state_repo
# from app.repositories.user_repo import user_repo
# from app.repositories.user_type_repo import user_type_repo
# from app.schemas.affidavit_schema import (
#     DocumentCreate,
#     DocumentCreateForm,
#     DocumentPayment,
#     DocumentSearchResponse,
#     LastestAffidavits,
#     ReceiptInResponse,
#     SearchResult,
#     SlimDocumentInResponse,
#     TemplateBase,
#     TemplateContent,
#     TemplateInResponse,
#     UpdateDocument,
#     serialize_mongo_document,
#     template_list_serialiser,
# )
# from app.schemas.category_schema import CategoryInResponse, FullCategoryInResponse
# from app.schemas.court_system_schema import CourtSystemInDB
# from app.schemas.email_schema import UserCreationTemplateVariables
# from app.schemas.payment_schema import PaymentCreate
# from app.schemas.shared_schema import SlimUserInResponse
# from app.schemas.stats_schema import PublicDashboardStat
# from app.schemas.user_schema import UserCreate, UserCreateForm, UserInResponse
# from app.schemas.user_type_schema import UserTypeInDB
# from commonLib.response.response_schema import GenericResponse, create_response

# # Import pagination schemas (you can also place these in a separate file as shown above)
# from app.schemas.pagination_schema import PaginationRequest, PaginationMeta, PaginatedResponse

# router = APIRouter()

# PUBLIC_FRONTEND_BASE_URL = settings.PUBLIC_FRONTEND_BASE_URL
# VERIFY_EMAIL_LINK = settings.VERIFY_EMAIL_LINK
# CREATE_ACCOUNT_TEMPLATE_ID = settings.CREATE_ACCOUNT_TEMPLATE_ID

# # ───────────────────────────────────────────────
# # Helper: Validate ObjectId
# def validate_objectid(document_id: str) -> ObjectId:
#     if not is_valid_objectid(document_id):
#         logger.error(f"Invalid ObjectId format: {document_id}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID format"
#         )
#     return ObjectId(document_id)

# # ───────────────────────────────────────────────
# # Endpoints with Pagination

# @router.get("/search", response_model=PaginatedResponse[Dict[str, Any]])
# async def search_documents(
#     query: str,
#     pagination: PaginationRequest = Depends(),
#     current_user: User = Depends(get_currently_authenticated_user)
# ):
#     """
#     Search for documents by name for the current user with pagination.
#     """
#     if not query:
#         logger.warning("Empty search query provided")
#         raise HTTPException(status_code=400, detail="Query parameter is required")
#     try:
#         filter_query = {
#             "name": {"$regex": f"^{query}", "$options": "i"},
#             "created_by_id": current_user.id,
#         }
#         total_count = await document_collection.count_documents(filter_query)
#         skip = (pagination.page - 1) * pagination.per_page
#         cursor = document_collection.find(filter_query).skip(skip).limit(pagination.per_page)
#         documents = await cursor.to_list(length=pagination.per_page)
#         total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
#         meta = PaginationMeta(
#             page=pagination.page,
#             per_page=pagination.per_page,
#             total_count=total_count,
#             total_pages=total_pages,
#         )
#         result = {"documents": serialize_mongo_document(documents)}
#         logger.info(f"Search query '{query}' executed successfully")
#         return PaginatedResponse(data=result, meta=meta)
#     except Exception as e:
#         logger.error("Error during document search", exc_info=True)
#         raise HTTPException(status_code=500, detail="Error searching for document")


# @router.get("/my_documents", dependencies=[Depends(authenticated_user_dependencies)], 
#             response_model=PaginatedResponse[Dict[str, Any]])
# async def get_documents(
#     pagination: PaginationRequest = Depends(),
#     current_user: User = Depends(get_currently_authenticated_user)
# ):
#     """
#     Retrieve non-archived documents for the current user with pagination.
#     """
#     try:
#         filter_query = {
#             "created_by_id": current_user.id,
#             "is_archived": False
#         }
#         total_count = await document_collection.count_documents(filter_query)
#         skip = (pagination.page - 1) * pagination.per_page
#         cursor = document_collection.find(filter_query).sort("created_at", -1).skip(skip).limit(pagination.per_page)
#         documents = await cursor.to_list(length=pagination.per_page)
#         total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
#         meta = PaginationMeta(
#             page=pagination.page,
#             per_page=pagination.per_page,
#             total_count=total_count,
#             total_pages=total_pages
#         )
#         logger.info(f"{len(documents)} documents retrieved for user {current_user.email} (page {pagination.page})")
#         return PaginatedResponse(data={"documents": serialize_mongo_document(documents)}, meta=meta)
#     except Exception as e:
#         logger.error("Error fetching documents", exc_info=True)
#         raise HTTPException(status_code=500, detail="Error fetching documents")


# @router.get("/get_archived_documents", dependencies=[Depends(authenticated_user_dependencies)], 
#             response_model=PaginatedResponse[Dict[str, Any]])
# async def get_archived_documents(
#     pagination: PaginationRequest = Depends(),
#     current_user: User = Depends(get_currently_authenticated_user)
# ):
#     """
#     Retrieve archived documents for the current user with pagination.
#     """
#     try:
#         filter_query = {
#             "created_by_id": current_user.id,
#             "is_archived": True
#         }
#         total_count = await document_collection.count_documents(filter_query)
#         skip = (pagination.page - 1) * pagination.per_page
#         cursor = document_collection.find(filter_query).skip(skip).limit(pagination.per_page)
#         documents = await cursor.to_list(length=pagination.per_page)
#         total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
#         meta = PaginationMeta(
#             page=pagination.page,
#             per_page=pagination.per_page,
#             total_count=total_count,
#             total_pages=total_pages
#         )
#         msg = "Archived documents retrieved successfully" if documents else "No Documents Found"
#         logger.info(f"Archived documents retrieval: {msg}")
#         return PaginatedResponse(data={"documents": serialize_mongo_document(documents)}, meta=meta)
#     except Exception as e:
#         logger.error("Error fetching archived documents", exc_info=True)
#         raise HTTPException(status_code=500, detail="Error fetching archived documents")


# @router.get(
#     "/get_templates",
#     response_model=PaginatedResponse[List[TemplateInResponse]],
#     dependencies=[Depends(authenticated_user_dependencies)]
# )
# async def get_templates(
#     pagination: PaginationRequest = Depends()
# ):
#     """
#     Retrieve all active templates with pagination.
#     """
#     try:
#         filter_query = {"is_disabled": False}
#         total_count = await template_collection.count_documents(filter_query)
#         skip = (pagination.page - 1) * pagination.per_page
#         templates_cursor = template_collection.find(filter_query).skip(skip).limit(pagination.per_page)
#         templates = await templates_cursor.to_list(length=pagination.per_page)
#         total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
#         meta = PaginationMeta(
#             page=pagination.page,
#             per_page=pagination.per_page,
#             total_count=total_count,
#             total_pages=total_pages
#         )
#         if not templates:
#             logger.info("No templates found")
#             return PaginatedResponse(data=[], meta=meta)
#         serialized = serialize_mongo_document(templates)
#         logger.info("Templates retrieved successfully")
#         # Map each template to the TemplateInResponse schema
#         data = [
#             TemplateInResponse(
#                 id=t.get("id"),
#                 name=t.get("name"),
#                 description=t.get("description"),
#                 content=t.get("content"),
#                 price=t.get("price"),
#                 category_id=t.get("category_id"),
#             )
#             for t in serialized
#         ]
#         return PaginatedResponse(data=data, meta=meta)
#     except Exception as e:
#         logger.error("Error retrieving templates", exc_info=True)
#         raise HTTPException(status_code=500, detail="Error fetching templates")


# @router.get(
#     "/get_templates_by_category/{category_id}",
#     response_model=PaginatedResponse[List[TemplateInResponse]],
#     dependencies=[Depends(authenticated_user_dependencies)]
# )
# async def get_templates_by_category(
#     category_id: str,
#     pagination: PaginationRequest = Depends()
# ):
#     """
#     Retrieve all active templates for a given category with pagination.
#     """
#     try:
#         filter_query = {"is_disabled": False, "category_id": category_id}
#         total_count = await template_collection.count_documents(filter_query)
#         skip = (pagination.page - 1) * pagination.per_page
#         templates_cursor = template_collection.find(filter_query).skip(skip).limit(pagination.per_page)
#         templates = await templates_cursor.to_list(length=pagination.per_page)
#         total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
#         meta = PaginationMeta(
#             page=pagination.page,
#             per_page=pagination.per_page,
#             total_count=total_count,
#             total_pages=total_pages
#         )
#         if not templates:
#             logger.info(f"No templates found for category {category_id}")
#             return PaginatedResponse(data=[], meta=meta)
#         serialized = serialize_mongo_document(templates)
#         logger.info(f"Templates for category {category_id} retrieved successfully")
#         data = [
#             TemplateInResponse(
#                 id=t.get("id"),
#                 name=t.get("name"),
#                 description=t.get("description"),
#                 content=t.get("content"),
#                 price=t.get("price"),
#                 category_id=t.get("category_id"),
#             )
#             for t in serialized
#         ]
#         return PaginatedResponse(data=data, meta=meta)
#     except Exception as e:
#         logger.error("Error retrieving templates by category", exc_info=True)
#         raise HTTPException(status_code=500, detail="Error fetching templates by category")


# @router.get(
#     "/get_states", response_model=PaginatedResponse[List[CourtSystemInDB]]
# )
# def get_states(db: Session = Depends(get_db), pagination: PaginationRequest = Depends()):
#     """
#     Retrieve a paginated list of all states.
#     """
#     try:
#         states_list = state_repo.get_all(db)
#         total_count = len(states_list)
#         # Simple in-memory pagination since states list is usually small
#         start = (pagination.page - 1) * pagination.per_page
#         end = start + pagination.per_page
#         paged_states = states_list[start:end]
#         total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
#         meta = PaginationMeta(
#             page=pagination.page,
#             per_page=pagination.per_page,
#             total_count=total_count,
#             total_pages=total_pages,
#         )
#         logger.info(f"{len(paged_states)} states retrieved (page {pagination.page})")
#         data = [CourtSystemInDB(id=state.id, name=state.name) for state in paged_states]
#         return PaginatedResponse(data=data, meta=meta)
#     except Exception as e:
#         logger.error("Error retrieving states", exc_info=True)
#         raise HTTPException(status_code=500, detail="Error retrieving states")


# @router.get(
#     "/get_jurisdictions_by_state/{state_id}",
#     response_model=PaginatedResponse[List[CourtSystemInDB]],
# )
# def get_jurisdictions_by_states(
#     state_id: str, db: Session = Depends(get_db), pagination: PaginationRequest = Depends()
# ):
#     """
#     Retrieve all jurisdictions for a given state with pagination.
#     """
#     try:
#         jurisdictions = db.query(Jurisdiction).filter(Jurisdiction.state_id == state_id).all()
#         total_count = len(jurisdictions)
#         start = (pagination.page - 1) * pagination.per_page
#         end = start + pagination.per_page
#         paged_jurisdictions = jurisdictions[start:end]
#         total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
#         meta = PaginationMeta(
#             page=pagination.page,
#             per_page=pagination.per_page,
#             total_count=total_count,
#             total_pages=total_pages,
#         )
#         logger.info(f"{len(paged_jurisdictions)} jurisdictions retrieved for state {state_id} (page {pagination.page})")
#         data = [CourtSystemInDB(id=j.id, name=j.name) for j in paged_jurisdictions]
#         return PaginatedResponse(data=data, meta=meta)
#     except Exception as e:
#         logger.error("Error retrieving jurisdictions", exc_info=True)
#         raise HTTPException(status_code=500, detail="Error retrieving jurisdictions")


# @router.get(
#     "/get_courts_by_jursdiction/{jurisdiction_id}",
#     response_model=PaginatedResponse[List[CourtSystemInDB]],
# )
# def get_courts_by_jurisdiction(
#     jurisdiction_id: str, db: Session = Depends(get_db), pagination: PaginationRequest = Depends()
# ):
#     """
#     Retrieve all courts for a given jurisdiction with pagination.
#     """
#     try:
#         courts = db.query(Court).filter(Court.jurisdiction_id == jurisdiction_id).all()
#         total_count = len(courts)
#         start = (pagination.page - 1) * pagination.per_page
#         end = start + pagination.per_page
#         paged_courts = courts[start:end]
#         total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
#         meta = PaginationMeta(
#             page=pagination.page,
#             per_page=pagination.per_page,
#             total_count=total_count,
#             total_pages=total_pages,
#         )
#         logger.info(f"{len(paged_courts)} courts retrieved for jurisdiction {jurisdiction_id} (page {pagination.page})")
#         data = [CourtSystemInDB(id=c.id, name=c.name) for c in paged_courts]
#         return PaginatedResponse(data=data, meta=meta)
#     except Exception as e:
#         logger.error("Error retrieving courts by jurisdiction", exc_info=True)
#         raise HTTPException(status_code=500, detail="Error retrieving courts")


# @router.get("/get_affidavit_categories")
# async def get_categories(db: Session = Depends(get_db), pagination: PaginationRequest = Depends()):
#     """
#     Retrieve all affidavit categories with associated templates with pagination.
#     """
#     try:
#         categories = category_repo.get_all(db)
#         total_count = len(categories)
#         start = (pagination.page - 1) * pagination.per_page
#         end = start + pagination.per_page
#         paged_categories = categories[start:end]
#         total_pages = (total_count + pagination.per_page - 1) // pagination.per_page
#         meta = PaginationMeta(
#             page=pagination.page,
#             per_page=pagination.per_page,
#             total_count=total_count,
#             total_pages=total_pages,
#         )
#         full_categories = []
#         for category in paged_categories:
#             templates_cursor = template_collection.find({"category_id": category.id}).sort([("updated_at", -1), ("created_at", -1)])
#             templates = await templates_cursor.to_list(length=1000)
#             full_categories.append(
#                 FullCategoryInResponse(
#                     name=category.name,
#                     id=category.id,
#                     created_by=SlimUserInResponse(
#                         id=category.user.id,
#                         first_name=category.user.first_name,
#                         last_name=category.user.last_name,
#                         email=category.user.email,
#                     ),
#                     date_created=category.CreatedAt,
#                     templates=[serialize_mongo_document(t) for t in templates],
#                 )
#             )
#         logger.info("Affidavit categories retrieved successfully")
#         return create_response(
#             data=full_categories,
#             status_code=status.HTTP_200_OK,
#             message="Categories Retrieved Successfully",
#             # Optionally, you could wrap the result in a pagination response as well:
#             # data=PaginatedResponse(data=full_categories, meta=meta)
#         )
#     except Exception as e:
#         logger.error("Error retrieving affidavit categories", exc_info=True)
#         raise HTTPException(status_code=500, detail="Error retrieving categories")
