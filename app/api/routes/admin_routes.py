
import datetime
import uuid
from typing import List, Dict, Any, Optional

from app.api.routes.court_system_routes import populate_data
from bson import ObjectId
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.authentication import (
    admin_permission_dependency,
    admin_and_head_of_unit_permission_dependency,
    get_currently_authenticated_user,
)
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    ServerException,
    UnauthorizedEndpointException,
)
from app.core.services.email import email_service
from app.core.services.invitation import process_user_invite
from app.core.services.jwt import jwt_service
from app.core.settings.configurations import settings
from app.core.settings.logs.handler import logger
from app.database.sessions.mongo_client import document_collection, template_collection
from app.models.court_system_models import Court, Jurisdiction, State
from app.models.user_invite_models import UserInvite
from app.models.user_model import User
from app.models.user_type_model import UserType
from app.repositories.category_repo import category_repo
from app.repositories.court_system_repo import court_repo, jurisdiction_repo, state_repo
from app.repositories.user_invite_repo import user_invite_repo
from app.repositories.user_repo import user_repo
from app.repositories.user_type_repo import user_type_repo
from app.schemas.affidavit_schema import (
    LastestAffidavits,
    SlimDocumentInResponse,
    SlimTemplateInResponse,
    TemplateBase,
    TemplateCreate,
    TemplateCreateForm,
    TemplateInResponse,
    serialize_mongo_document,
)
from app.schemas.category_schema import (
    Category,
    CategoryCreate,
    CategoryInResponse,
    FullCategoryInResponse,
)
from app.schemas.court_system_schema import (
    CourtBase,
    CourtInResponse,
    CourtSystemBase,
    CourtSystemInDB,
    JurisdictionInResponse,
    SlimCourtInResponse,
    SlimJurisdictionInResponse,
)
from app.schemas.email_schema import (
    OperationsInviteTemplateVariables,
    UserCreationTemplateVariables,
)
from app.schemas.shared_schema import SlimUserInResponse, DateRange
from app.schemas.stats_schema import AdminDashboardStat, HeadOfUnitDashboardStat
from app.schemas.user_schema import (
    AcceptedInviteResponse,
    AdminInResponse,
    AllUsers,
    CommissionerInResponse,
    CreateInvite,
    FullCommissionerInResponse,
    HeadOfUnitInResponse,
    InviteOperationsForm,
    OperationsCreateForm,
    UserCreate,
    UserInResponse,
)
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import GenericResponse, create_response

router = APIRouter()

# --- Helper Functions ---

async def aggregate_total_revenue() -> int:
    """Run a MongoDB aggregation pipeline and return total revenue."""
    pipeline = [
        {"$match": {"$or": [{"status": "PAID"}, {"is_attested": True}]}},
        {"$group": {"_id": None, "total_amount": {"$sum": "$amount_paid"}}},
    ]
    cursor = document_collection.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    return result[0]["total_amount"] if result else 0

def get_user_type_or_404(db: Session, type_name: str) -> UserType:
    user_type = user_type_repo.get_by_name(db=db, name=type_name)
    if not user_type:
        logger.warning(f"User type '{type_name}' not found")
        raise DoesNotExistException(entity_name="User type")
    return user_type

# --- Endpoints ---

@router.get("/get_dashboard_stats",status_code=status.HTTP_200_OK, dependencies=[Depends(admin_permission_dependency)], response_model=GenericResponse[AdminDashboardStat])
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Return aggregated dashboard statistics.
    """
    try:
        total_affidavits = await document_collection.count_documents({})
        total_users = user_repo.get_count(db)
        total_templates = await template_collection.count_documents({})
        total_revenue = await aggregate_total_revenue()

        stats = AdminDashboardStat(
            total_affidavits=total_affidavits,
            total_users=total_users,
            total_templates=total_templates,
            total_revenue=total_revenue,
        )
        logger.info("Dashboard stats successfully retrieved")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Dashboard Stats fetched successfully.",
            data=stats,
        )
    except Exception as e:
        logger.error("Error in get_dashboard_stats", exc_info=True)
        raise ServerException(detail="Error fetching dashboard stats.")


@router.get("/get_head_of_units",status_code=status.HTTP_200_OK, response_model=GenericResponse[List[HeadOfUnitInResponse]], dependencies=[Depends(admin_permission_dependency)])
def get_unit_heads(db: Session = Depends(get_db)):
    """
    Retrieve head-of-unit users with nested jurisdiction, courts, and commissioners.
    """
    try:
        user_type = get_user_type_or_404(db, settings.HEAD_OF_UNIT_USER_TYPE)
        head_of_units = user_repo.get_users_by_user_type(db=db, user_type_id=user_type.id)
        
        response = [
            HeadOfUnitInResponse(
                id=hu.id,
                first_name=hu.first_name,
                last_name=hu.last_name,
                email=hu.email,
                date_created=hu.CreatedAt,
                user_type=UserTypeInDB(id=hu.user_type.id, name=hu.user_type.name),
                verify_token="",
                is_active=hu.is_active,
                jurisdiction=CourtSystemInDB(
                    name=hu.head_of_unit.jurisdiction.name,
                    id=hu.head_of_unit.jurisdiction.id,
                ),
                courts=[CourtSystemInDB(name=c.name, id=c.id) for c in hu.head_of_unit.jurisdiction.courts],
                commissioners=[
                    UserInResponse(
                        id=comm.id,
                        first_name=comm.first_name,
                        last_name=comm.last_name,
                        email=comm.email,
                        user_type=UserTypeInDB(id=comm.user_type.id, name=comm.user_type.name),
                        verify_token="",
                        is_active=comm.is_active,
                    )
                    for hu in head_of_units
                    for c in hu.head_of_unit.jurisdiction.courts
                    for cp in c.commissioner_profiles
                    for comm in [cp.user]
                ],
            )
            for hu in head_of_units
        ]
        logger.info("Head of units retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Head Of Units retrieved successfully",
            data=response,
        )
    except Exception as e:
        logger.error("Error retrieving head of units", exc_info=True)
        raise ServerException(detail="Error retrieving head of unit users.")

@router.get(
    "/get_latest_affidavits",
    status_code=status.HTTP_200_OK,

    dependencies=[Depends(admin_permission_dependency)],

)
async def get_latest_affidavits(db: Session = Depends(get_db)):
    """
    Retrieve the latest 5 affidavits (with status PAID or attested), enriched with court and template details.
    """
    try:
        # Filter for affidavits that are either PAID or attested,
        # then sort by created_at descending and limit to 5.
        filter_query = {"$or": [{"status": "PAID"}, {"is_attested": True}]}
        docs = await document_collection.find(filter_query).sort("created_at", -1).to_list(length=5)
        
        if not docs:
            logger.info("No affidavits found")
            return create_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No affidavits found",
                data=[],
            )
        
        docs = serialize_mongo_document(docs)
        enriched_docs = []
        for doc in docs:
            # Retrieve the court name using court_repo
            court = court_repo.get(db, id=doc.get("court_id"))
            # Retrieve the template name from the template collection
            template = await template_collection.find_one({"_id": ObjectId(doc.get("template_id"))})
            doc["court"] = court.name if court else "Unknown Court"
            doc["template"] = template["name"] if template else "Unknown Template"
            enriched_docs.append(doc)
        
        logger.info("Latest affidavits retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Latest affidavits retrieved successfully",
            data=enriched_docs,
        )
    except Exception as e:
        logger.error("Error fetching latest affidavits", exc_info=True)
        raise ServerException(detail="Error fetching latest affidavits.")

@router.get(
    "/get_commissioners",
     status_code=status.HTTP_200_OK,
    dependencies=[Depends(admin_permission_dependency)],
    response_model=GenericResponse[List[CommissionerInResponse]],
)
async def get_commissioners(db: Session = Depends(get_db)):
    """
    Retrieve commissioner users along with their attested documents.
    """
    try:
        # Retrieve the commissioner user type; this helper will raise an exception if not found.
        user_type = get_user_type_or_404(db, settings.COMMISSIONER_USER_TYPE)
        commissioners = user_repo.get_users_by_user_type(db, user_type_id=user_type.id)
        
        result = []
        for commissioner in commissioners:
            docs = await document_collection.find({"commissioner_id": commissioner.id}).to_list(length=1000)
            docs_serialized = [
                SlimDocumentInResponse(
                    id=str(doc["_id"]),
                    name=doc.get("name", ""),
                    attested_date=doc.get("attestation_date", ""),
                    created_at=doc.get("created_at", ""),
                    status=doc.get("status", ""),
                )
                for doc in docs
            ]
            comm_resp = CommissionerInResponse(
                id=commissioner.id,
                first_name=commissioner.first_name,
                last_name=commissioner.last_name,
                email=commissioner.email,
                user_type=UserTypeInDB(id=commissioner.user_type.id, name=commissioner.user_type.name),
                verify_token="some_verify_token",
                court=CourtSystemInDB(
                    id=commissioner.commissioner_profile.court.id,
                    name=commissioner.commissioner_profile.court.name,
                ),
                is_active=commissioner.is_active,
                attested_documents=docs_serialized,
                date_created=commissioner.CreatedAt,
            )
            result.append(comm_resp)
        
        logger.info("Commissioners retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Commissioners retrieved successfully",
            data=result,
        )
    except Exception as e:
        logger.error("Error retrieving commissioners", exc_info=True)
        raise ServerException(detail="Error retrieving commissioners.")

@router.get(
    "/get_all_jurisdictions",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(admin_permission_dependency)],
    response_model=GenericResponse[List[SlimJurisdictionInResponse]],
)
def get_all_jurisdictions(db: Session = Depends(get_db)):
    """
    Retrieve all jurisdictions with basic details.
    """
    # try:
    jurisdictions = jurisdiction_repo.get_all(db)
    data = []
    for jurisdiction in jurisdictions:
            
            data.append(SlimJurisdictionInResponse(
                id=jurisdiction.id,
                name=jurisdiction.name,
                 date_created=jurisdiction.CreatedAt,
                 courts=len(jurisdiction.courts),
    head_of_unit=f"{jurisdiction.head_of_unit.user.first_name} {jurisdiction.head_of_unit.user.last_name}" if jurisdiction.head_of_unit else 'N/A'
                    ,
                
            ))
            # data.append(
            #     JurisdictionInResponse(
            #         id=jurisdiction.id,
            #         name=jurisdiction.name,
            #         date_created=jurisdiction.CreatedAt,
            #         state=CourtSystemInDB(
            #             id=jurisdiction.state.id, 
            #             name=jurisdiction.state.name
            #         ),
            #         courts=len(jurisdiction.courts),
            #         head_of_unit=(
            #             SlimUserInResponse(
            #                 id=jurisdiction.head_of_unit.user.id,
            #                 first_name=jurisdiction.head_of_unit.user.first_name,
            #                 last_name=jurisdiction.head_of_unit.user.last_name,
            #                 email=jurisdiction.head_of_unit.user.email,
            #             )
            #             if jurisdiction.head_of_unit else None
            #         ),
            #     )
            # )
    
    
    
    
    
    logger.info("Jurisdictions retrieved successfully")
    return create_response(
            status_code=status.HTTP_200_OK,
            message="Jurisdictions retrieved successfully",
            data=data,
        )
    # except Exception as e:
    #     logger.error("Error retrieving user data: " + str(e), exc_info=True)
    #     raise ServerException(detail="Error retrieving jurisdictions.")




@router.get(
    "/general_users",
    dependencies=[Depends(admin_permission_dependency)],
    # response_model=GenericResponse[List[PublicInResponse]]
)
async def get_users(
    db: Session = Depends(get_db),
  
):
    users = user_repo.get_all(db)
    response = []
    for user in users:
        pipeline = [
            {
                "$match": {
                    "created_by_id": user.id,
                    "$or": [{"status": "PAID"}, {"is_attested": True}],
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_amount": {"$sum": "$amount_paid"},
                }
            },
        ]
        total_saved = await document_collection.find(
            {"created_by_id": user.id, "status": "SAVED"}
        ).to_list(length=1000)
        total_paid = await document_collection.find(
            {"created_by_id": user.id, "status": "PAID"}
        ).to_list(length=1000)
        total_attested = await document_collection.find(
            {"created_by_id": user.id, "status": "ATTESTED"}
        ).to_list(length=1000)
        total_documents = await document_collection.find(
            {"created_by_id": user.id}
        ).to_list(length=1000)
        total_amount_result = await document_collection.aggregate(pipeline).to_list(
            length=100
        )
        if total_amount_result:
            total_amount = total_amount_result[0]["total_amount"]
        else:
            total_amount = 0

        new_user = dict(
            total_documents=[
                SlimDocumentInResponse(
                    id=str(document["_id"]),
                    name=document.get("name", ""),
                    price=document.get("price", 0),
                    attestation_date=document.get("attest", ""),
                    created_at=document.get("created_at", ""),
                    status=document.get("status", ""),
                )
                for document in total_documents
            ],
            total_paid=[
                SlimDocumentInResponse(
                    id=str(document["_id"]),
                    name=document.get("name", ""),
                    price=document.get("price", 0),
                    attestation_date=document.get("attest", ""),
                    created_at=document.get("created_at", ""),
                    status=document.get("status", ""),
                )
                for document in total_paid
            ],
            total_attested=[
                SlimDocumentInResponse(
                    id=str(document["_id"]),
                    name=document.get("name", ""),
                    price=document.get("price", 0),
                    attestation_date=document.get("attest", ""),
                    created_at=document.get("created_at", ""),
                    status=document.get("status", ""),
                )
                for document in total_attested
            ],
            total_saved=[
                SlimDocumentInResponse(
                    id=str(document["_id"]),
                    name=document.get("name", ""),
                    price=document.get("price", 0),
                    attestation_date=document.get("attest", ""),
                    created_at=document.get("created_at", ""),
                    status=document.get("status", ""),
                )
                for document in total_saved
            ],
            id=user.id,
            total_amount=total_amount,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            is_active=user.is_active,
            user_type=UserTypeInDB(id=user.user_type.id, name=user.user_type.name),
            date_created=user.CreatedAt,
            verify_token="",
        )
        response.append(new_user)


    total_users = user_repo.get_count(db)
    # metadata = {"total": total_users, "limit": limit, "skip": skip}
    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"Users information retrieved successfully.",
        data=response,
        # metadata="metadata",
    )
# @router.get("/general_users", dependencies=[Depends(admin_permission_dependency)])
# async def get_general_users(
#     db: Session = Depends(get_db),
#     # skip: int = Query(0, ge=0),
#     # limit: int = Query(0, ge=0),
# ):
#     """
#     Retrieve paginated list of general users with associated document details.
#     """
#     try:
#         users = user_repo.get_all(db)
#         response = []
#         for user in users:
#             pipeline = [
#                 {"$match": {"created_by_id": user.id, "$or": [{"status": "PAID"}, {"is_attested": True}]}},
#                 {"$group": {"_id": None, "total_amount": {"$sum": "$amount_paid"}}},
#             ]
#             total_amount_result = await document_collection.aggregate(pipeline).to_list(length=1)
#             total_amount = total_amount_result[0]["total_amount"] if total_amount_result else 0

#             async def fetch_docs(status_value: str) -> List[SlimDocumentInResponse]:
#                 try:
#                     docs = await document_collection.find({"created_by_id": user.id, "status": status_value}).to_list(length=1000)
#                     return [SlimDocumentInResponse(
#                         id=str(doc["_id"]),
#                         name=doc.get("name", ""),
#                         price=doc.get("price", 0),
#                         attestation_date=doc.get("attest", ""),
#                         created_at=doc.get("created_at", ""),
#                         status=doc.get("status", ""),
#                     ) for doc in docs]
#                 except Exception as e:
#                     logger.error(f"Error fetching documents with status {status_value}: {e}")
#                     return []

#             new_user = {
#                 "id": user.id,
#                 "first_name": user.first_name,
#                 "last_name": user.last_name,
#                 "email": user.email,
#                 "is_active": user.is_active,
#                 "user_type": UserTypeInDB(id=user.user_type.id, name=user.user_type.name),
#                 "date_created": user.CreatedAt,
#                 "verify_token": "",
#                 "total_documents": await document_collection.find({"created_by_id": user.id}).count(),
#                 "total_amount": total_amount,
#                 "total_saved": fetch_docs("SAVED"),
#                 "total_paid": fetch_docs("PAID"),
#                 "total_attested": fetch_docs("ATTESTED"),
#             }
#             response.append(new_user)
#         # metadata = {"total": user_repo.get_count(db), "limit": limit, "skip": skip}
#         logger.info("General user data retrieved successfully")
#         return create_response(
#             status_code=status.HTTP_200_OK,
#             message="Users information retrieved successfully.",
#             data=response,
#             # metadata=metadata,
#         )
#     except Exception as e:
#         logger.error(e, exc_info=True)
#         raise ServerException(detail="Error retrieving user data.")


@router.post("/invite_personel", dependencies=[Depends(admin_permission_dependency)], status_code=status.HTTP_200_OK)
async def invite_users(
    users: List[InviteOperationsForm],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_currently_authenticated_user),
    db: Session = Depends(get_db),
):
    """
    Process a list of user invitations.
    """
    try:
        for idx, user_data in enumerate(users):
            logger.debug(f"Inviting user {idx + 1} of {len(users)}")
            await process_user_invite(user_data, current_user, db, background_tasks)
        logger.info("All invitations processed successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Users invited successfully.",
        )
    except Exception as e:
        logger.error("Error processing invitations", exc_info=True)
        raise ServerException(detail="Error processing invitations.")


@router.put("/accept_invite/{token}", status_code=status.HTTP_200_OK, response_model=GenericResponse)
async def accept_invite(token: str, db: Session = Depends(get_db)):
    """
    Accept an invitation given a token.
    """
    try:
        invite_info = jwt_service.get_user_id_from_token(token)
        invite_id = invite_info.get("id")
    except Exception as e:
        logger.error("Token validation error", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Token validation error: {str(e)}")

    db_invite: UserInvite = user_invite_repo.get(db, id=invite_id)
    if not db_invite:
        logger.warning("Invite not found")
        raise HTTPException(status_code=404, detail="Invite not found or invalid.")
    if db_invite.is_accepted:
        logger.warning("Invite already accepted")
        raise HTTPException(status_code=400, detail="This invitation has already been accepted.")

    user_invite_repo.mark_invite_as_accepted(db, db_obj=db_invite)
    logger.info("Invitation accepted successfully")
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Invite accepted successfully",
        data={"invite_id": db_invite.id},
    )


@router.get("/get_public_users")
def get_public_users(db: Session = Depends(get_db)):
    """
    Return all public users.
    """
    try:
        user_type = get_user_type_or_404(db, settings.PUBLIC_USER_TYPE)
        users = user_type.users
        response = [
            UserInResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                is_active=user.is_active,
                verify_token="",
                user_type=UserTypeInDB(id=user.user_type.id, name=user.user_type.name),
            )
            for user in users
        ]
        logger.info("Public users retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Public Users retrieved successfully",
            data=response,
        )
    except Exception as e:
        logger.error("Error fetching public users", exc_info=True)
        raise ServerException(detail="Error fetching public users.")


@router.get("/get_all_users")
def get_all_users(db: Session = Depends(get_db)):
    """
    Return paginated list of all users.
    """
    try:
        users = user_repo.get_all(db)
        response = [
            AllUsers(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                is_active=user.is_active,
                user_type=UserTypeInDB(name=user.user_type.name, id=user.user_type.id),
                date_created=user.CreatedAt,
                verify_token="",
            )
            for user in users
        ]
        logger.info("All users retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="All Users retrieved successfully.",
            data=response,
       
        )
    except Exception as e:
        logger.error("Error retrieving all users", exc_info=True)
        raise ServerException(detail="Error retrieving all users.")


@router.get("/get_all_admins", dependencies=[Depends(admin_permission_dependency)], response_model=GenericResponse[List[AdminInResponse]])
async def get_all_admins(db: Session = Depends(get_db), current_user=Depends(get_currently_authenticated_user)):
    """
    Return all admin users.
    """
    try:
        user_type = get_user_type_or_404(db, settings.ADMIN_USER_TYPE)
        admins = user_repo.get_users_by_user_type(db, user_type_id=user_type.id)
        result = []
        for admin in admins:
            templates_created = await template_collection.find({"created_by_id": admin.id}).to_list(length=1000)
            templates_serialized = [
                SlimTemplateInResponse(
                    id=str(t["_id"]),
                    name=t.get("name", ""),
                    price=t.get("price", 0),
                    description=t.get("description", ""),
                    category_id=t.get("category", ""),
                )
                for t in templates_created
            ]
            admin_resp = AdminInResponse(
                id=admin.id,
                date_created=admin.CreatedAt,
                first_name=admin.first_name,
                last_name=admin.last_name,
                email=admin.email,
                is_active=admin.is_active,
                verify_token="",
                user_type=UserTypeInDB(id=admin.user_type.id, name=admin.user_type.name),
                users_invited=[
                    UserInResponse(
                        id=inv.user.id,
                        first_name=inv.first_name,
                        last_name=inv.last_name,
                        email=inv.email,
                        is_active=inv.user.is_active,
                        verify_token="",
                        user_type=UserTypeInDB(id=inv.user_type.id, name=inv.user_type.name),
                    )
                    for inv in admin.invited_by
                ],
                templates_created=templates_serialized,
            )
            result.append(admin_resp)
        logger.info("Admin users retrieved successfully")
        return create_response(
            message="Admins retrieved successfully",
            status_code=status.HTTP_200_OK,
            data=result,
        )
    except Exception as e:
        logger.error("Error retrieving admin users", exc_info=True)
        raise ServerException(detail="Error retrieving admin users.")


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=GenericResponse[UserInResponse])
def create_admin(admin_in: OperationsCreateForm, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Create a new admin account using an invitation.
    """
    db_invite = user_invite_repo.get(db, id=admin_in.invite_id)
    if not db_invite:
        raise DoesNotExistException(detail="Invitation does not exist or is invalid.")
    if not db_invite.is_accepted:
        raise HTTPException(status_code=403, detail="Cannot use un-accepted invites for creating new accounts.")
    if db_invite.user_type.name != settings.ADMIN_USER_TYPE:
        raise UnauthorizedEndpointException()
    if user_repo.get_by_email(db, email=db_invite.email):
        raise AlreadyExistsException(detail="This email address already exists.")

    admin_obj = UserCreate(
        first_name=db_invite.first_name,
        last_name=db_invite.last_name,
        user_type_id=db_invite.user_type_id,
        password=admin_in.password,
        email=db_invite.email,
    )
    try:
        new_admin = user_repo.create(db=db, obj_in=admin_obj)
        verify_token = user_repo.create_verification_token(email=new_admin.email, db=db)
        verification_link = f"{settings.ADMIN_FRONTEND_BASE_URL}{settings.VERIFY_EMAIL_LINK}{verify_token}"
        template_dict = UserCreationTemplateVariables(
            name=f"{new_admin.first_name} {new_admin.last_name}",
            action_url=verification_link,
        ).dict()
        logger.info(f"Verification link: {verification_link}")
        email_service.send_email_with_template(
            db=db,
            template_id=settings.CREATE_ACCOUNT_TEMPLATE_ID,
            template_dict=template_dict,
            recipient=new_admin.email,
            background_tasks=background_tasks,
        )
        logger.info("Admin account created successfully")
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message="Account created successfully",
            data=UserInResponse(
                id=new_admin.id,
                first_name=new_admin.first_name,
                last_name=new_admin.last_name,
                email=new_admin.email,
                verify_token=verify_token,
                user_type=UserTypeInDB(name=new_admin.user_type.name, id=new_admin.user_type.id),
                is_active=new_admin.is_active,
            ),
        )
    except Exception as e:
        logger.error("Error creating admin account", exc_info=True)
        raise ServerException(detail="Error creating admin account.")


@router.get("/me",status_code=status.HTTP_200_OK ,dependencies=[Depends(admin_permission_dependency)], response_model=GenericResponse[UserInResponse])
def retrieve_current_admin(current_user=Depends(get_currently_authenticated_user)) -> UserInResponse:
    """
    Retrieve the currently logged-in admin's profile.
    """
    logger.info(f"Retrieving profile for admin {current_user.email}")
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Profile retrieved successfully",
        data=UserInResponse(
            id=current_user.id,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            email=current_user.email,
            is_active=current_user.is_active,
            user_type=UserTypeInDB(id=current_user.user_type.id, name=current_user.user_type.name),
            verify_token="",
        ),
    )

# --- Court System Endpoints ---

@router.post("/create_state", status_code=status.HTTP_201_CREATED, dependencies=[Depends(admin_permission_dependency)])
def create_state(state: CourtSystemBase, db: Session = Depends(get_db)):
    """
    Create a new state.
    """
    try:
        state_exist = state_repo.get_by_field(db=db, field_name="name", field_value=state.name.title())
        if state_exist:
            raise AlreadyExistsException(f"{state.name} already exists")
        # Note: Ensure you pass the correct data to the repository create method.
        new_state = state_repo.create(db, obj_in=state)
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message=f"{state.name} created successfully",
            data=CourtSystemInDB(id=str(new_state.id), name=new_state.name),
        )
    except Exception as e:
        logger.error("Error creating state", exc_info=True)
        raise ServerException(detail="Error creating state.")


@router.get("/get_state/{id}", status_code=status.HTTP_200_OK, response_model=GenericResponse[CourtSystemInDB], dependencies=[Depends(admin_permission_dependency)])
def get_state(id: int, db: Session = Depends(get_db)):
    """
    Retrieve state information by its ID.
    """
    try:
        state_obj = state_repo.get(db, id=id)
        if not state_obj:
            raise DoesNotExistException(detail=f"State with id {id} does not exist.")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="State Retrieved Successfully",
            data=CourtSystemInDB(id=str(state_obj.id), name=state_obj.name),
        )
    except Exception as e:
        logger.error("Error retrieving state", exc_info=True)
        raise ServerException(detail="Error retrieving state.")


@router.get("/get_states", status_code=status.HTTP_200_OK, response_model=GenericResponse[List[CourtSystemInDB]], dependencies=[Depends(admin_permission_dependency)])
def get_all_states(db: Session = Depends(get_db)):
    """
    Retrieve all states.
    """
    try:
        states_list = state_repo.get_all(db)
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Successful",
            data=[CourtSystemInDB(id=str(s.id), name=s.name) for s in states_list],
        )
    except Exception as e:
        logger.error("Error retrieving states", exc_info=True)
        raise ServerException(detail="Error retrieving states.")


@router.get("/populate_court_system")
def populate_court_system(db: Session = Depends(get_db)):
    """
    Populate the court system with predefined data.
    """
    try:
        populate_data(db)
        logger.info("Court system populated successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Court system populated successfully",
        )
    except Exception as e:
        logger.error("Error populating court system", exc_info=True)
        raise ServerException(detail="Error populating court system.")


@router.get("/jurisdictions/{jurisdiction_id}", status_code=status.HTTP_200_OK, response_model=GenericResponse[JurisdictionInResponse])
async def get_jurisdiction(jurisdiction_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a jurisdiction with its details.
    """
    try:
        jurisdiction = jurisdiction_repo.get(db, id=jurisdiction_id)
        if not jurisdiction:
            raise DoesNotExistException(detail="Jurisdiction does not exist")
        # Aggregate document count across all courts in this jurisdiction
        jurisdiction_documents = []
        for court in jurisdiction.courts:
            docs = await document_collection.find({"court_id": court.id, "status": {"$in": ["PAID", "ATTESTED"]}}).to_list(length=1000)
            jurisdiction_documents.extend(serialize_mongo_document(docs))
        response = JurisdictionInResponse(
            id=jurisdiction.id,
            name=jurisdiction.name,
            date_created=jurisdiction.CreatedAt,
            state=CourtSystemInDB(id=jurisdiction.state.id, name=jurisdiction.state.name),
            courts=[
                SlimCourtInResponse(
                    id=c.id,
                    date_created=c.CreatedAt,
                    name=c.name,
                    commissioners=len(c.commissioner_profiles),
                    documents=await document_collection.count_documents({"court_id": c.id}),
                )
                for c in jurisdiction.courts
            ],
            head_of_unit=(
                SlimUserInResponse(
                    id=jurisdiction.head_of_unit.user.id,
                    first_name=jurisdiction.head_of_unit.user.first_name,
                    last_name=jurisdiction.head_of_unit.user.last_name,
                    email=jurisdiction.head_of_unit.user.email,
                )
                if jurisdiction.head_of_unit else None
            ),
            commissioners=[
                SlimUserInResponse(
                    id=comm.id,
                    first_name=comm.first_name,
                    last_name=comm.last_name,
                    email=comm.email,
                )
                for c in jurisdiction.courts
                for cp in c.commissioner_profiles
                for comm in [cp.user]
            ],
            documents=len(jurisdiction_documents),
        )
        logger.info(f"Jurisdiction {jurisdiction.name} retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{jurisdiction.name} Retrieved successfully",
            data=response,
        )
    except Exception as e:
        logger.error("Error retrieving jurisdiction", exc_info=True)
        raise ServerException(detail="Error retrieving jurisdiction.")


@router.get("/jurisdictions/{jurisdiction_id}/courts", dependencies=[Depends(admin_permission_dependency)])
def get_courts_by_jurisdiction(jurisdiction_id: str, db: Session = Depends(get_db)):
    """
    Retrieve all courts within a given jurisdiction.
    """
    try:
        courts = db.query(Court).filter(Court.jurisdiction_id == jurisdiction_id).all()
        response = [
            CourtBase(
                id=c.id,
                date_created=c.CreatedAt,
                name=c.name,
                state=CourtSystemInDB(id=c.jurisdiction.state.id, name=c.jurisdiction.state.name),
                Jurisdiction=[CourtSystemInDB(id=c.jurisdiction.id, name=c.jurisdiction.name)],
                head_of_unit=SlimUserInResponse(
                    id=c.jurisdiction.head_of_unit.id,
                    first_name=c.jurisdiction.head_of_unit.user.first_name,
                    last_name=c.jurisdiction.head_of_unit.user.last_name,
                    email=c.jurisdiction.head_of_unit.user.email,
                ),
            )
            for c in courts
        ]
        logger.info("Courts by jurisdiction retrieved successfully")
        return create_response(
            message="Courts retrieved successfully",
            status_code=status.HTTP_200_OK,
            data=response,
        )
    except Exception as e:
        logger.error("Error retrieving courts by jurisdiction", exc_info=True)
        raise ServerException(detail="Error retrieving courts by jurisdiction.")


@router.get("/get_court/{court_id}", dependencies=[Depends(admin_permission_dependency)])
async def get_court(court_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a single court’s detailed information.
    """
    try:
        court = court_repo.get(db, id=court_id)
        if not court:
            raise DoesNotExistException(detail="Court does not exist")
        docs = await document_collection.find({"court_id": court.id, "status": {"$in": ["PAID", "ATTESTED"]}}).to_list(length=1000)
        court_documents = serialize_mongo_document(docs)
        response = CourtInResponse(
            id=court.id,
            name=court.name,
            date_created=court.CreatedAt,
            jurisdiction=CourtSystemInDB(id=court.jurisdiction.id, name=court.jurisdiction.name),
            commissioners=[
                SlimUserInResponse(
                    id=cp.user.id,
                    first_name=cp.user.first_name,
                    last_name=cp.user.last_name,
                    email=cp.user.email,
                    is_active=cp.user.is_active,
                )
                for cp in court.commissioner_profiles
            ],
            documents=[
                SlimDocumentInResponse(
                    id=str(doc.get("id", "")),
                    name=doc.get("name", ""),
                    price=doc.get("price", 0),
                    attestation_date=doc.get("attest", ""),
                    created_at=doc.get("created_at", ""),
                    status=doc.get("status", ""),
                )
                for doc in court_documents
            ],
        )
        logger.info(f"Court {court.name} retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{court.name} retrieved successfully",
            data=response,
        )
    except Exception as e:
        logger.error("Error retrieving court", exc_info=True)
        raise ServerException(detail="Error retrieving court.")


# --- Affidavits (Templates/Categories) Endpoints ---

@router.post("/create_template", dependencies=[Depends(admin_permission_dependency)], status_code=status.HTTP_201_CREATED, response_model=GenericResponse[TemplateBase])
async def create_template(template_in: TemplateCreateForm, current_user: User = Depends(get_currently_authenticated_user)):
    """
    Create a new affidavit template.
    """
    try:
        template_dict = template_in.dict()
        existing_template = await template_collection.find_one({"name": template_dict["name"]})
        if existing_template:
            raise HTTPException(status_code=400, detail="Template with the given name already exists")
        template_dict = TemplateCreate(**template_dict, created_by_id=current_user.id).dict()
        result = await template_collection.insert_one(template_dict)
        if not result.acknowledged:
            logger.error("Failed to insert template")
            raise HTTPException(status_code=500, detail="Failed to create template")
        new_template = await template_collection.find_one({"_id": result.inserted_id})
        logger.info(f"Template {new_template.get('name')} created successfully")
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message=f"{new_template.get('name')} template Created Successfully",
            data=serialize_mongo_document(new_template),
        )
    except Exception as e:
        logger.error("Error creating template", exc_info=True)
        raise ServerException(detail="Error creating template.")


@router.get("/get_templates", dependencies=[Depends(admin_permission_dependency)], response_model=GenericResponse[List[TemplateBase]])
async def get_templates():
    """
    Retrieve all available templates.
    """
    try:
        templates = await template_collection.find().to_list(length=100)
        if not templates:
            logger.info("No templates found")
            return create_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No templates found",
                data=[],
            )
        logger.info("Templates retrieved successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Templates retrieved successfully",
            data=serialize_mongo_document(templates),
        )
    except Exception as e:
        logger.error("Error fetching templates", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching templates")


@router.get("/get_template/{template_id}", dependencies=[Depends(admin_permission_dependency)], response_model=GenericResponse[TemplateBase])
async def get_template(template_id: str):
    """
    Retrieve a specific template by its ID.
    """
    try:
        object_id = ObjectId(template_id)
    except Exception as e:
        logger.error(f"Invalid template ID format: {template_id}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Invalid ID format: {template_id}")
    logger.info(f"Fetching template with ID: {object_id}")
    template_obj = await template_collection.find_one({"_id": object_id})
    if not template_obj:
        logger.info("No template found")
        raise HTTPException(status_code=404, detail=f"Template with ID {template_id} does not exist")
    template_obj = serialize_mongo_document(template_obj)
    logger.info(f"Template {template_obj.get('name')} retrieved successfully")
    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{template_obj.get('name')} retrieved successfully",
        data=template_obj,
    )


@router.patch("/disable_template/{template_id}", dependencies=[Depends(admin_permission_dependency)], status_code=status.HTTP_200_OK, response_model=GenericResponse[TemplateBase])
async def disable_template(template_id: str):
    """
    Disable a template.
    """
    try:
        template_dict = {"is_disabled": True, "updated_at": datetime.datetime.utcnow()}
        object_id = ObjectId(template_id)
        existing_template = await template_collection.find_one({"_id": object_id})
        if not existing_template:
            raise HTTPException(status_code=404, detail="Template does not exist")
        update_result = await template_collection.update_one({"_id": existing_template["_id"]}, {"$set": template_dict})
        if not update_result.modified_count:
            logger.error("Failed to update template")
            raise HTTPException(status_code=500, detail="Failed to update template")
        updated_template = await template_collection.find_one({"_id": existing_template["_id"]})
        logger.info(f"Template {updated_template.get('name')} disabled successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{updated_template.get('name')} template disabled successfully",
        )
    except Exception as e:
        logger.error("Error disabling template", exc_info=True)
        raise HTTPException(status_code=500, detail="Error disabling template")


@router.patch("/enable_template/{template_id}", dependencies=[Depends(admin_permission_dependency)], status_code=status.HTTP_200_OK, response_model=GenericResponse[TemplateBase])
async def enable_template(template_id: str):
    """
    Enable a previously disabled template.
    """
    try:
        template_dict = {"is_disabled": False, "updated_at": datetime.datetime.utcnow()}
        object_id = ObjectId(template_id)
        existing_template = await template_collection.find_one({"_id": object_id})
        if not existing_template:
            raise HTTPException(status_code=404, detail="Template does not exist")
        update_result = await template_collection.update_one({"_id": existing_template["_id"]}, {"$set": template_dict})
        if not update_result.modified_count:
            logger.error("Failed to update template")
            raise HTTPException(status_code=500, detail="Failed to update template")
        updated_template = await template_collection.find_one({"_id": existing_template["_id"]})
        logger.info(f"Template {updated_template.get('name')} enabled successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{updated_template.get('name')} template enabled successfully",
        )
    except Exception as e:
        logger.error("Error enabling template", exc_info=True)
        raise HTTPException(status_code=500, detail="Error enabling template")


@router.patch("/update_template/{template_id}", dependencies=[Depends(admin_permission_dependency)], status_code=status.HTTP_200_OK, response_model=GenericResponse[TemplateBase])
async def update_template(template_in: TemplateBase, current_user: User = Depends(get_currently_authenticated_user)):
    """
    Update an existing template.
    """
    try:
        template_dict = {**template_in.dict(), "updated_at": datetime.datetime.utcnow()}
        object_id = ObjectId(template_dict["id"])
        existing_template = await template_collection.find_one({"_id": object_id})
        if not existing_template:
            raise HTTPException(status_code=404, detail="Template does not exist")
        update_result = await template_collection.update_one({"_id": existing_template["_id"]}, {"$set": template_dict})
        if not update_result.modified_count:
            logger.error("Failed to update template")
            raise HTTPException(status_code=500, detail="Failed to update template")
        updated_template = await template_collection.find_one({"_id": existing_template["_id"]})
        logger.info(f"Template {updated_template.get('name')} updated successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{updated_template.get('name')} template updated successfully",
            data=serialize_mongo_document(updated_template),
        )
    except Exception as e:
        logger.error("Error updating template", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating template")


@router.put("/activate_user/{user_id}", dependencies=[Depends(admin_permission_dependency)])
def activate_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_currently_authenticated_user)):
    """
    Activate a user account.
    """
    try:
        db_user = user_repo.get(db, id=user_id)
        if not db_user:
            raise DoesNotExistException(detail="User does not exist")
        if user_id == current_user.id:
            raise HTTPException(status_code=403, detail="You cannot activate yourself")
        if db_user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account is already active.")
        user_repo.activate(db, db_obj=db_user)
        logger.info(f"User {db_user.first_name} {db_user.last_name} activated successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{db_user.first_name} {db_user.last_name} activated successfully",
        )
    except Exception as e:
        logger.error("Error activating user", exc_info=True)
        raise ServerException(detail="Error activating user.")


@router.put("/deactivate_user/{user_id}", dependencies=[Depends(admin_permission_dependency)])
def deactivate_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_currently_authenticated_user)):
    """
    Deactivate a user account.
    """
    try:
        db_user = user_repo.get(db, id=user_id)
        if not db_user:
            raise DoesNotExistException(detail="User does not exist")
        if user_id == current_user.id:
            raise HTTPException(status_code=403, detail="You cannot deactivate yourself")
        if not db_user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account is already inactive.")
        user_repo.deactivate(db, db_obj=db_user)
        logger.info(f"User {db_user.first_name} {db_user.last_name} deactivated successfully")
        return create_response(
            status_code=status.HTTP_200_OK,
            message=f"{db_user.first_name} {db_user.last_name} deactivated successfully",
        )
    except Exception as e:
        logger.error("Error deactivating user", exc_info=True)
        raise ServerException(detail="Error deactivating user.")


@router.get("/get_affidavit_categories")
async def get_categories(db: Session = Depends(get_db)):
    """
    Retrieve all affidavit categories along with their templates.
    """
    try:
        categories = category_repo.get_all(db)
        full_categories = []
        for category in categories:
            templates = await template_collection.find({"category_id": category.id}).sort([("updated_at", -1), ("created_at", -1)]).to_list(length=1000)
            full_category = FullCategoryInResponse(
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
            full_categories.append(full_category)
        logger.info("Affidavit categories retrieved successfully")
        return create_response(
            data=full_categories,
            status_code=status.HTTP_200_OK,
            message="Categories Retrieved Successfully",
        )
    except Exception as e:
        logger.error("Error retrieving affidavit categories", exc_info=True)
        raise ServerException(detail="Error retrieving affidavit categories.")



@router.get("/get_slim_categories")
async def get_categories(db: Session = Depends(get_db)):
    """
    Retrieve all affidavit categories with summary info:
    - name
    - date created
    - date updated (from the latest template, or the category creation date if none exist)
    - total number of templates.
    Categories are ordered from newest to oldest based on the creation date.
    """
    try:
        categories = category_repo.get_all(db)
        summarized_categories = []
        for category in categories:
            templates = await template_collection.find(
                {"category_id": category.id}
            ).sort([("updated_at", -1), ("created_at", -1)]).to_list(length=1000)
            
            total_templates = len(templates)
            date_updated = templates[0]["updated_at"] if total_templates > 0 else category.CreatedAt
            
            summarized_category = {
                "id" :category.id,
                "name": category.name,
                "date_created": category.CreatedAt,
                "date_updated": date_updated,
                "total_templates": total_templates,
            }
            summarized_categories.append(summarized_category)
        
        # Sort the categories from newest to oldest based on the date_created field
        summarized_categories.sort(key=lambda x: x["date_created"], reverse=True)
        
        logger.info("Affidavit categories retrieved successfully")
        return create_response(
            data=summarized_categories,
            status_code=status.HTTP_200_OK,
            message="Categories Retrieved Successfully",
        )
    except Exception as e:
        logger.error("Error retrieving affidavit categories", exc_info=True)
        raise ServerException(detail="Error retrieving affidavit categories.")





@router.post("/create_affidavit_category")
def create_category(category_name: Category, db: Session = Depends(get_db), current_user: User = Depends(get_currently_authenticated_user)):
    """
    Create a new affidavit category.
    """
    try:
        category_exists = category_repo.get_by_name(db, name=category_name.name)
        if category_exists:
            raise AlreadyExistsException(entity_name="A Category with this name or a similar name.")
        category_in = CategoryCreate(name=category_name.name.title(), created_by_id=current_user.id)
        db_category = category_repo.create(db, obj_in=category_in)
        logger.info(f"Category {db_category.name} created successfully")
        return create_response(
            data=CategoryInResponse(name=db_category.name, id=db_category.id),
            status_code=status.HTTP_201_CREATED,
            message=f"{db_category.name} Category Created Successfully",
        )
    except Exception as e:
        logger.error("Error creating affidavit category", exc_info=True)
        raise ServerException(detail="Error creating affidavit category.")


@router.get("/get_category/{catgory_id}")
def get_category(category_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a single affidavit category by its ID.
    """
    try:
        db_category = category_repo.get(db, id=category_id)
        if not db_category:
            raise DoesNotExistException(detail="This category does not exist.")
        logger.info(f"Category {db_category.name} retrieved successfully")
        return create_response(
            data=db_category,
            status_code=status.HTTP_200_OK,
            message=f"{db_category.name} retrieved successfully",
        )
    except Exception as e:
        logger.error("Error retrieving category", exc_info=True)
        raise ServerException(detail="Error retrieving category.")


@router.put("/update_category/{category_id}")
def update_category(category: CategoryInResponse, db: Session = Depends(get_db)):
    """
    Update an affidavit category (only the name field).
    """
    try:
        db_category = category_repo.get(db, id=category.id)
        if not db_category:
            raise DoesNotExistException(detail="This category does not exist.")
        category.name = category.name.title()
        new_db_category = category_repo.update(db, db_obj=db_category, obj_in=category.dict(exclude_unset=True))
        logger.info(f"Category {db_category.name} updated successfully")
        return create_response(
            data=CategoryInResponse(name=new_db_category.name, id=new_db_category.id),
            status_code=status.HTTP_200_OK,
            message=f"{db_category.name} retrieved successfully",
        )
    except Exception as e:
        logger.error("Error updating category", exc_info=True)
        raise ServerException(detail="Error updating category.")


@router.get("/get_invites", response_model=GenericResponse[List], dependencies=[Depends(admin_permission_dependency)])
def get_all_invites(db: Session = Depends(get_db)):
    """
    Retrieve all user invitations.
    """
    try:
        current_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
        invites = (
            db.query(
                UserInvite.id,
                UserInvite.first_name,
                UserInvite.last_name,
                UserInvite.email,
                UserInvite.is_accepted,
                UserInvite.accepted_at,
                UserInvite.CreatedAt,
                UserType.name.label("user_type"),
                UserType.id.label("user_type_id"),
            )
            .join(UserType, UserInvite.user_type_id == UserType.id)
            .all()
        )
        result = []
        for invite in invites:
            created_at = invite.CreatedAt.replace(tzinfo=datetime.timezone.utc) if invite.CreatedAt else None
            accepted_at = invite.accepted_at.replace(tzinfo=datetime.timezone.utc) if invite.accepted_at else None
            if invite.is_accepted:
                invite_status = "ACCEPTED"
            elif accepted_at is None and created_at and (current_time - created_at) < datetime.timedelta(hours=24):
                invite_status = "PENDING"
            else:
                invite_status = "EXPIRED"
            result.append({
                "id": invite.id,
                "first_name": invite.first_name,
                "last_name": invite.last_name,
                "email": invite.email,
                "status": invite_status,
                "date_created": created_at.isoformat() if created_at else None,
                "date_accepted": accepted_at.isoformat() if accepted_at else None,
                "user_type": {"id": invite.user_type_id, "name": invite.user_type},
            })
        logger.info("Invites retrieved successfully")
        return create_response(
            data=result,
            message="User invites retrieved successfully",
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error("Error retrieving invites", exc_info=True)
        raise ServerException(detail="Error retrieving invites.")


@router.delete("/delete_invite/{invite_id}", response_model=GenericResponse)
def delete_invite(invite_id: str, db: Session = Depends(get_db)):
    """
    Delete a user invitation.
    """
    try:
        deleted_invite = user_invite_repo.remove(db, id=invite_id)
        logger.info(f"Invite {deleted_invite.id} deleted successfully")
        return create_response(
            message=f"Invite to {deleted_invite.first_name} {deleted_invite.last_name} deleted successfully",
            status_code=status.HTTP_200_OK,
        )
    except Exception as e:
        logger.error("Error deleting invite", exc_info=True)
        raise ServerException(detail="Error deleting invite.")

