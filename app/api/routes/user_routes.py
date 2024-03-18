from typing import List
import uuid
from app.core.services.utils.utils import is_valid_objectid
from app.models.court_system_models import Court, Jurisdiction
from app.schemas.court_system_schema import CourtSystemInDB
from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from loguru import logger
from sqlalchemy.orm import Session
from app.api.dependencies.authentication import (
    get_currently_authenticated_user,
    authenticated_user_dependencies,
)
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import AlreadyExistsException, DoesNotExistException
from app.core.services.email import email_service
from app.models.user_model import User
from app.repositories.user_repo import user_repo
from app.repositories.user_type_repo import user_type_repo
from app.schemas.affidavit_schema import (
    SlimDocumentInResponse,
    TemplateBase,
    TemplateInResponse,
    document_list_serialiser,
    serialize_mongo_document,
    template_individual_serializer,
    template_list_serialiser,
)
from app.repositories.court_system_repo import state_repo
from app.schemas.email_schema import UserCreationTemplateVariables
from app.schemas.stats_schema import PublicDashboardStat
from app.schemas.user_schema import (
    UserCreate,
    UserCreateForm,
    UserInResponse,
    UserWithToken,
)
from postmarker import core
from app.database.sessions.mongo_client import template_collection, document_collection
from app.repositories.court_system_repo import court_repo
from app.core.settings.configurations import settings
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import GenericResponse, create_response


router = APIRouter()

PUBLIC_FRONTEND_BASE_URL = settings.PUBLIC_FRONTEND_BASE_URL
VERIFY_EMAIL_LINK = settings.VERIFY_EMAIL_LINK
CREATE_ACCOUNT_TEMPLATE_ID = settings.CREATE_ACCOUNT_TEMPLATE_ID


@router.get("/get_dashboard_stats")
def get_dashboard_stats():

    total_saved = 10
    total_paid = 60
    total_attested = 40
    total_response = 20
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Dashboard stats retrieved successfully",
        data=PublicDashboardStat(
            total_saved=total_saved,
            total_paid=total_paid,
            total_attested=total_attested,
            total_rejected=total_response,
        ),
    )


@router.post("/user", response_model=GenericResponse[UserInResponse])
def create_user(
    user_in: UserCreateForm,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user_exist = user_repo.get_by_email(email=user_in.email, db=db)
    if user_exist:
        raise AlreadyExistsException(
            detail=f"User with email {user_in.email} already exists"
        )
    # Fetch the user type
    user_type = user_type_repo.get_by_name(name=settings.PUBLIC_USER_TYPE, db=db)

    if not user_type:
        raise DoesNotExistException(detail="User type not found.")

    user_in = UserCreate(**user_in.dict(), user_type_id=user_type.id)
    try:
        new_user = user_repo.create(obj_in=user_in, db=db)
        verify_token = user_repo.create_verification_token(email=new_user.email, db=db)
        verification_link = (
            f"{PUBLIC_FRONTEND_BASE_URL}{VERIFY_EMAIL_LINK}={verify_token}"
        )
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

    except IntegrityError as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the user.",
        )

    return create_response(
        status_code=status.HTTP_201_CREATED,
        message="Account created successfully",
        data=UserInResponse(
            id=new_user.id,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            email=new_user.email,
            verify_token=verify_token,
            is_active=new_user.is_active,
            user_type=UserTypeInDB(name=user_type.name, id=user_type.id),
        ),
    )


@router.get("/me")
def retrieve_current_user(
    current_user: User = Depends(get_currently_authenticated_user),
) -> UserInResponse:
    """
    This is used to retrieve the currently logged-in user's profile.
    You need to send a token in and it returns a full profile of the currently logged in user.
    You send the token in as a header of the form \n
    <b>Authorization</b> : 'Token <b> {JWT} </b>'
    """
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
async def get_documents(current_user: User = Depends(get_currently_authenticated_user)):
    try:
        documents = (
            await document_collection.find({"created_by_id": current_user.id})
            .sort("created_at", -1)
            .to_list(length=100)
        )  # Set a reasonable limit
        if not documents:
            logger.info("No documents found")
            return []
        return create_response(
            status_code=status.HTTP_200_OK,
            data=document_list_serialiser(documents),
            message=f"Documents retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching documents")


@router.get(
    "/get_my_latest_affidavits",
    #   dependencies=[Depends(authenticated_user_dependencies)]
)
async def get_my_latest_affidavits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    try:
        documents = (
            await document_collection.find({"created_by_id": current_user.id})
            .sort("created_at", -1)
            .limit(5)
            .to_list(length=5)
        )
        if not documents:
            logger.info("No documents found")
            return []

        documents = serialize_mongo_document(documents)

        enriched_documents = []
        for document in documents:
            court = court_repo.get(db, id=document["court_id"])
            template = await template_collection.find_one(
                {"_id": ObjectId(document["template_id"])}
            )
            document["court"] = court.name if court else "Unknown Court"
            document["template"] = template["name"] if template else "Unknown Template"
            enriched_documents.append(document)

        return create_response(
            status_code=status.HTTP_200_OK,
            data=[
                SlimDocumentInResponse(
                    name=document["name"],
                    court=document["court"],
                    template=document["template"],
                    id=document["_id"],
                    status=document["status"],
                    created_at=document["created_at"],
                )
                for document in enriched_documents
            ],
            message="Documents retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching documents")


@router.get("/get_document/{document_id}")
async def get_document(
    document_id: str,
    current_user: User = Depends(get_currently_authenticated_user),
):
    if not ObjectId.is_valid(document_id):
        logger.error(f"Invalid ObjectId format: {document_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid document ID format"
        )

    try:
        document = await document_collection.find_one(
            {"_id": ObjectId(document_id), "created_by_id": current_user.id}
        )
        if not document:
            logger.error(
                f"Could not find document by ID {document_id} for the user ID {current_user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        document = serialize_mongo_document(document)
        return document
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the document",
        )


@router.get(
    "/get_templates",
    # response_model=GenericResponse[List[TemplateBase]],
    # dependencies=[Depends(authenticated_user_dependencies)],
)
async def get_templates():
    templates = await template_collection.find({"is_disabled": False}).to_list(
        length=100
    )
    if not templates:
        logger.info("No templates found")
        return create_response(
            status_code=status.HTTP_404_NOT_FOUND,
            message="No templates found",
            data=[],
        )
    templates = template_list_serialiser(templates)
    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"Templates retrieved successfully",
        data=[
            TemplateInResponse(
                id=template["id"],
                name=template["name"],
                description=template["description"],
                content=template["content"],
                price=template["price"],
                category="hkjhkhk",
            )
            for template in templates
        ],
    )


@router.get(
    "/get_template/{template_id}",
    # response_model=GenericResponse[TemplateBase],
    dependencies=[Depends(authenticated_user_dependencies)],
)
async def get_template_for_document_creation(
    template_id: str,
):
    try:
        object_id = ObjectId(template_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ID format: {template_id}")
    logger.info(f"Fetching template with ID: {object_id}")

    template_obj = await template_collection.find_one({"_id": object_id})
    if template_obj["is_disabled"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template is not available at the moment",
        )
    if template_obj:
        logger.info(f"Found template: {template_obj}")
    else:
        logger.info("No template found")

    if not template_obj:
        raise HTTPException(
            status_code=404,
            detail=f"Template with ID {template_id} does not exist",
        )

    # Assuming individual_serialiser is a valid function
    template_obj = template_individual_serializer(template_obj)
    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{template_obj['name']} retrieved successfully",
        data=TemplateInResponse(
            id=template_obj["id"],
            name=template_obj["name"],
            description=template_obj["description"],
            content=template_obj["content"],
            price=template_obj["price"],
            category=template_obj["category"],
        ),
    )


@router.get("/pay_for_document")
def pay_for_document(
    current_user: User = Depends(get_currently_authenticated_user),
) -> UserInResponse:
    """
    This is used to retrieve the currently logged-in user's profile.
    You need to send a token in and it returns a full profile of the currently logged in user.
    You send the token in as a header of the form \n
    <b>Authorization</b> : 'Token <b> {JWT} </b>'
    """
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


@router.get("/get_document_status_counts")
def pay_for_document(
    current_user: User = Depends(get_currently_authenticated_user),
) -> UserInResponse:
    """
    This is used to retrieve the currently logged-in user's profile.
    You need to send a token in and it returns a full profile of the currently logged in user.
    You send the token in as a header of the form \n
    <b>Authorization</b> : 'Token <b> {JWT} </b>'
    """
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


@router.get("/get_states")
def get_states(db: Session = Depends(get_db)):
    states = state_repo.get_all(db)

    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{len(states)} States Retrieved Successfully!",
        data=[CourtSystemInDB(id=state.id, name=state.name) for state in states],
    )


@router.get("/get_jurisdictions_by_state/{state_id}")
def get_jurisdictions_by_states(state_id: int, db: Session = Depends(get_db)):
    jurisdictions = (
        db.query(Jurisdiction).filter(Jurisdiction.state_id == state_id).all()
    )
    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{len(jurisdictions)} States Retrieved Successfully!",
        data=[
            CourtSystemInDB(id=jurisdiction.id, name=jurisdiction.name)
            for jurisdiction in jurisdictions
        ],
    )


@router.get("/get_courts_by_jursdiction/{jurisdiction_id}")
def get_courts_by_jurisdiction(jurisdiction_id: str, db: Session = Depends(get_db)):
    courts = db.query(Court).filter(Court.jurisdiction_id == jurisdiction_id).all()
    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{len(courts)} States Retrieved Successfully!",
        data=[CourtSystemInDB(id=court.id, name=court.name) for court in courts],
    )
