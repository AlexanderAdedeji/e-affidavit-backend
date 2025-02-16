import datetime
import uuid
from typing import List

from bson import ObjectId
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
    Body,
    Request
)
from sqlalchemy.orm import Session

# Import authentication and DB dependencies
from app.api.dependencies.authentication import (
    admin_and_head_of_unit_permission_dependency,
    commissioner_permission_dependency,
    get_currently_authenticated_user,
)
from app.api.dependencies.db import get_db

# Import error classes and settings
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    UnauthorizedEndpointException,
)
from app.core.services.email import email_service
from app.core.services.jwt import jwt_service
from app.core.settings.configurations import settings
from app.core.settings.logs.handler import logger

# Import database collections (Motor client for MongoDB)
from app.database.sessions.mongo_client import document_collection, template_collection

# Import models and repositories
from app.models.user_model import User
from app.models.user_invite_models import UserInvite
from app.repositories.commissioner_profile_repo import comm_profile_repo
from app.repositories.head_of_unit_repo import head_of_unit_repo
from app.repositories.user_invite_repo import user_invite_repo
from app.repositories.user_repo import user_repo
from app.repositories.user_type_repo import user_type_repo

# Import schemas
from app.schemas.affidavit_schema import (
    AttestDocument,
    SlimDocumentInResponse,
    serialize_mongo_document,
)
from app.schemas.court_system_schema import CourtSystemInDB
from app.schemas.email_schema import UserCreationTemplateVariables
from app.schemas.report_schema import CommissionerReport  # if needed
from app.schemas.user_schema import (
    CommissionerAttestation,
    CommissionerCreate,
    CommissionerInResponse,
    FullCommissionerInResponse,
    FullCommissionerProfile,
    OperationsCreateForm,
    UserCreate,
    UserInResponse,
)
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import GenericResponse, create_response

router = APIRouter()

# ─── HELPER FUNCTIONS ───────────────────────────────────────────────

async def build_commissioner_response(commissioner: User, db: Session) -> CommissionerInResponse:
    """
    Given a commissioner User model, fetches attested documents from MongoDB and builds a response object.
    """
    # Fetch documents associated with this commissioner asynchronously
    try:
        docs_cursor = document_collection.find({"commissioner_id": commissioner.id})
        attested_docs = await docs_cursor.to_list(length=1000)
    except Exception as e:
        logger.error("Error fetching documents for commissioner", exc_info=True)
        attested_docs = []
    docs_serialized = [
        SlimDocumentInResponse(
            id=str(doc["_id"]),
            name=doc.get("name", ""),
            attested_date=doc.get("attestation_date", ""),
            created_at=doc.get("created_at", ""),
            status=doc.get("status", ""),
        )
        for doc in attested_docs
    ]
    return CommissionerInResponse(
        id=commissioner.id,
        first_name=commissioner.first_name,
        last_name=commissioner.last_name,
        email=commissioner.email,
        user_type=UserTypeInDB(
            id=commissioner.user_type.id, name=commissioner.user_type.name
        ),
        verify_token="some_verify_token",  # You might generate a real token here if needed
        is_active=commissioner.is_active,
        court=CourtSystemInDB(
            id=commissioner.commissioner_profile.court.id,
            name=commissioner.commissioner_profile.court.name,
        ),
        attested_documents=docs_serialized,
        date_created=commissioner.CreatedAt,
    )

# ─── ENDPOINTS ──────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=GenericResponse[List[CommissionerInResponse]],
    dependencies=[Depends(admin_and_head_of_unit_permission_dependency)],
)
async def get_commissioners(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Retrieve commissioners. If the current user is a Head of Unit, only commissioners within their jurisdiction are returned.
    Otherwise, all commissioners are returned.
    """
    try:
        results: List[CommissionerInResponse] = []
        if current_user.user_type.name.lower() == settings.HEAD_OF_UNIT_USER_TYPE.lower():
            # Retrieve commissioner profiles under the head's jurisdiction
            commissioner_profiles = head_of_unit_repo.get_commissioners_under_jurisdiction(
                db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
            )
            commissioners = [profile.user for profile in commissioner_profiles]
        else:
            # Admin branch: retrieve all commissioners
            user_type = user_type_repo.get_by_name(db=db, name=settings.COMMISSIONER_USER_TYPE)
            if not user_type:
                logger.error("Commissioner user type not found")
                raise HTTPException(status_code=500, detail="Commissioner user type not found")
            commissioners = user_repo.get_users_by_user_type(db, user_type_id=user_type.id)
        # Build the detailed response for each commissioner
        for comm in commissioners:
            res = await build_commissioner_response(comm, db)
            results.append(res)
        logger.info("Commissioners retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Commissioners retrieved successfully",
            data=results,
        )
    except Exception as e:
        logger.error("Error retrieving commissioners", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving commissioners")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_commissioner(
    commissioner_in: OperationsCreateForm,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Create a new commissioner account based on an invitation.
    """
    try:
        # Validate invitation
        db_invite = user_invite_repo.get(db=db, id=commissioner_in.invite_id)
        if not db_invite:
            logger.warning("Invitation not found")
            raise DoesNotExistException(detail="Invitation does not exist or is invalid.")
        if not db_invite.is_accepted:
            logger.warning("Invitation not accepted")
            raise HTTPException(status_code=403, detail="Cannot use un-accepted invites for creating new accounts.")
        if db_invite.user_type.name != settings.COMMISSIONER_USER_TYPE:
            logger.warning("Invitation is not for a commissioner")
            raise HTTPException(status_code=403, detail="You do not have permission to access this endpoint.")
        if user_repo.get_by_email(db=db, email=db_invite.email):
            logger.warning("Email already in use")
            raise HTTPException(status_code=409, detail=f"User with email {db_invite.email} already exists.")

        # Create new commissioner user
        commissioner_obj = UserCreate(
            first_name=db_invite.first_name,
            last_name=db_invite.last_name,
            user_type_id=db_invite.user_type_id,
            password=commissioner_in.password,
            email=db_invite.email,
        )
        db_commissioner = user_repo.create(db=db, obj_in=commissioner_obj)
        if db_commissioner:
            # Create the associated commissioner profile
            commissioner_profile_in = CommissionerProfileCreate(
                commissioner_id=db_commissioner.id,
                court_id=db_invite.court_id,
                created_by_id=db_invite.invited_by_id,
            )
            comm_profile_repo.create(db=db, obj_in=commissioner_profile_in)
        verify_token = user_repo.create_verification_token(email=db_commissioner.email, db=db)
        verification_link = f"{settings.COURT_SYSTEM_FRONTEND_BASE_URL}{settings.VERIFY_EMAIL_LINK}{verify_token}"
        template_dict = UserCreationTemplateVariables(
            name=f"{db_commissioner.first_name} {db_commissioner.last_name}",
            action_url=verification_link,
        ).dict()
        logger.info(f"Verification link generated: {verification_link}")
        email_service.send_email_with_template(
            db=db,
            template_id=settings.CREATE_ACCOUNT_TEMPLATE_ID,
            template_dict=template_dict,
            recipient=db_commissioner.email,
            background_tasks=background_tasks,
        )
        logger.info("Commissioner account created successfully")
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message="Account created successfully",
            data=UserInResponse(
                id=db_commissioner.id,
                first_name=db_commissioner.first_name,
                last_name=db_commissioner.last_name,
                email=db_commissioner.email,
                verify_token=verify_token,
                user_type=UserTypeInDB(
                    id=db_commissioner.user_type.id,
                    name=db_commissioner.user_type.name,
                ),
                is_active=db_commissioner.is_active,
            ),
        )
    except Exception as e:
        logger.error("Error creating commissioner account", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating commissioner account.")


@router.get(
    "/me",
    dependencies=[Depends(commissioner_permission_dependency)],
    response_model=GenericResponse[FullCommissionerInResponse],
)
def get_current_commissioner(current_user=Depends(get_currently_authenticated_user)):
    """
    Retrieve the full profile of the currently authenticated commissioner.
    """
    try:
        if current_user.user_type.name.lower() != settings.COMMISSIONER_USER_TYPE.lower():
            logger.warning("Access denied: user is not a commissioner")
            raise UnauthorizedEndpointException(detail="You do not have access")
        # Build full profile response
        response = FullCommissionerInResponse(
            id=current_user.id,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            email=current_user.email,
            is_active=current_user.is_active,
            court=CourtSystemInDB(
                id=current_user.commissioner_profile.court.id,
                name=current_user.commissioner_profile.court.name,
            ),
        )
        logger.info("Commissioner profile retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Profile retrieved successfully",
            data=response,
        )
    except Exception as e:
        logger.error("Error retrieving commissioner profile", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving commissioner profile.")


@router.put("/update_attestation", dependencies=[Depends(commissioner_permission_dependency)])
def update_attestation(
    attestation: AttestDocument,
    db: Session = Depends(get_db),
    current_user=Depends(get_currently_authenticated_user),
):
    """
    Update the attestation details for the currently logged-in commissioner.
    """
    try:
        commissioner_profile = comm_profile_repo.get_profile_by_commissioner_id(db, commissioner_id=current_user.id)
        if not commissioner_profile:
            raise DoesNotExistException(entity_name="Commissioner profile not found")
        updated_profile = comm_profile_repo.updateAttestation(db, db_obj=commissioner_profile, attestation_obj=attestation)
        logger.info("Commissioner attestation updated successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Attestation updated successfully",
            data=updated_profile,
        )
    except Exception as e:
        logger.error("Error updating attestation", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating attestation.")


@router.put("/activate_commissioner/{commissioner_id}", dependencies=[Depends(admin_and_head_of_unit_permission_dependency)])
def activate_commissioner(commissioner_id: str, db: Session = Depends(get_db)):
    """
    Activate a commissioner account.
    """
    try:
        commissioner = user_repo.get(db, id=commissioner_id)
        if not commissioner:
            raise DoesNotExistException(detail="Commissioner does not exist")
        if commissioner.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account is already active.")
        user_repo.activate(db, db_obj=commissioner)
        logger.info(f"Commissioner {commissioner.first_name} {commissioner.last_name} activated successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{commissioner.first_name} {commissioner.last_name} activated successfully",
        )
    except Exception as e:
        logger.error("Error activating commissioner", exc_info=True)
        raise HTTPException(status_code=500, detail="Error activating commissioner.")


@router.put("/deactivate_commissioner/{commissioner_id}", dependencies=[Depends(admin_and_head_of_unit_permission_dependency)])
def deactivate_commissioner(commissioner_id: str, db: Session = Depends(get_db)):
    """
    Deactivate a commissioner account.
    """
    try:
        commissioner = user_repo.get(db, id=commissioner_id)
        if not commissioner:
            raise DoesNotExistException(detail="Commissioner does not exist")
        if not commissioner.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account is already inactive.")
        user_repo.deactivate(db, db_obj=commissioner)
        logger.info(f"Commissioner {commissioner.first_name} {commissioner.last_name} deactivated successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{commissioner.first_name} {commissioner.last_name} deactivated successfully",
        )
    except Exception as e:
        logger.error("Error deactivating commissioner", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deactivating commissioner.")


@router.get("/search_document")
async def search_document(document_name: str, current_user: User = Depends(get_currently_authenticated_user)):
    """
    Search for a document by name; ensure that the document belongs to the commissioner's court.
    """
    try:
        document = await document_collection.find_one({"name": document_name})
        if document is None:
            raise DoesNotExistException(detail="Document with provided name does not exist.")
        if document["court_id"] != current_user.commissioner_profile.court_id:
            raise UnauthorizedEndpointException(detail="You do not have access, you are not in this court")
        if document["status"] not in ["PAID", "ATTESTED"]:
            raise UnauthorizedEndpointException(detail="This document has not been paid for")
        logger.info(f"Document '{document_name}' retrieved successfully")
        return create_response(
            message="Document retrieved successfully",
            status_code=status.HTTP_200_OK,
            data=serialize_mongo_document(document),
        )
    except Exception as e:
        logger.error("Error searching for document", exc_info=True)
        raise HTTPException(status_code=500, detail="Error searching for document.")


@router.put("/attest_document/{document_id}")
async def attest_document(document_id: str, document_in: AttestDocument, current_user: User = Depends(get_currently_authenticated_user)):
    """
    Attest a document (mark it as attested) by the commissioner.
    """
    try:
        now = datetime.datetime.utcnow()
        update_data = document_in.dict(exclude_unset=True)
        update_data.update({
            "status": "ATTESTED",
            "commissioner_id": current_user.id,
            "is_attested": True,
            "attestation_date": now,
            "updated_at": now,
        })
        update_result = await document_collection.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": update_data}
        )
        if update_result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Document not found or no update made.")
        updated_document = await document_collection.find_one({"_id": ObjectId(document_id)})
        if not updated_document:
            raise HTTPException(status_code=404, detail="Document not found after update.")
        logger.info(f"Document '{updated_document.get('name')}' attested successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{updated_document.get('name')} has been attested successfully",
            data=None,
        )
    except Exception as e:
        logger.error("Error attesting document", exc_info=True)
        raise HTTPException(status_code=500, detail="Error attesting document.")


@router.get("/get_my_attestation", dependencies=[Depends(commissioner_permission_dependency)])
async def get_my_attestations(db: Session = Depends(get_db), current_user=Depends(get_currently_authenticated_user)):
    """
    Retrieve the attestation details (signature and stamp) for the currently logged-in commissioner.
    """
    try:
        commissioner_profile = comm_profile_repo.get_profile_by_commissioner_id(db=db, commissioner_id=current_user.id)
        if not commissioner_profile:
            raise DoesNotExistException(entity_name="Commissioner not found")
        if not commissioner_profile.signature:
            raise DoesNotExistException(entity_name="Commissioner signature not found")
        if not commissioner_profile.stamp:
            raise DoesNotExistException(entity_name="Commissioner Stamp not found")
        logger.info("Commissioner attestation retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Attestation retrieved successfully",
            data={"signature": commissioner_profile.signature, "stamp": commissioner_profile.stamp},
        )
    except Exception as e:
        logger.error("Error retrieving attestation", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving attestation.")
