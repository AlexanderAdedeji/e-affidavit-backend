from datetime import datetime
from typing import List
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger

from bson import ObjectId
from app.core.services.invitation import process_user_invite
from app.schemas.affidavit_schema import (
    SlimDocumentInResponse,
    SlimTemplateInResponse,
    TemplateBase,
    TemplateContent,
    TemplateCreate,
    TemplateCreateForm,
    TemplateInResponse,
    serialize_mongo_document,
    template_individual_serializer,
    template_list_serialiser,
)
from app.schemas.shared_schema import SlimUserInResponse
from app.schemas.stats_schema import AdminDashboardStat
from postmarker import core
from sqlalchemy.orm import Session
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    ServerException,
    UnauthorizedEndpointException,
)
from app.core.services.jwt import (
    generate_invitation_token,
    get_all_details_from_token,
    get_user_id_from_token,
)
from app.models.user_invite_models import UserInvite
from app.models.user_model import User
from app.core.settings.configurations import settings
from app.repositories.user_invite_repo import user_invite_repo
from app.repositories.user_repo import user_repo
from app.repositories.user_type_repo import user_type_repo
from app.api.dependencies.authentication import (
    admin_permission_dependency,
    get_token_details,
)
from app.schemas.court_system_schema import (
    CourtInResponse,
    CourtSystemInDB,
    JurisdictionInResponse,
    SlimCourtInResponse,
    SlimJurisdictionInResponse,
)
from app.schemas.email_schema import OperationsInviteTemplateVariables
from app.schemas.user_schema import (
    AcceptedInviteResponse,
    AdminInResponse,
    CommissionerInResponse,
    CreateInvite,
    FullCommissionerInResponse,
    InviteOperationsForm,
    OperationsCreateForm,
    UserCreate,
    UserInResponse,
)
from app.api.dependencies.authentication import get_currently_authenticated_user
from app.database.sessions.mongo_client import document_collection
from app.repositories.court_system_repo import jurisdiction_repo, court_repo
from app.core.services.email import email_service
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import create_response, GenericResponse
from app.database.sessions.mongo_client import template_collection

router = APIRouter()


@router.get("/get_dashboard_stats", dependencies=[Depends(admin_permission_dependency)])
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    This endpoint returns the number of users and invites in the system."""
    total_affidavits = await document_collection.count_documents({})
    total_users = user_repo.get_count(db)
    total_templates = await template_collection.count_documents({})

    pipeline = [
        {
            "$match": {
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

    total_revenue_cursor = document_collection.aggregate(pipeline)
    total_revenue = await total_revenue_cursor.to_list(length=1)

    return create_response(
        status_code=status.HTTP_200_OK,
        message="Dashboard Stats fetched successfully.",
        data=AdminDashboardStat(
            total_affidavits=total_affidavits,
            total_users=total_users,
            total_templates=total_templates,
            total_revenue=total_revenue[0]["total_amount"] if total_revenue else 0,
        ),
    )


@router.get("/get_head_of_units", dependencies=[Depends(admin_permission_dependency)])
def get_unit_heads(db: Session = Depends(get_db)):
    user_type = user_type_repo.get_by_name(db=db, name=settings.HEAD_OF_UNIT_USER_TYPE)
    if user_type is None:
        raise HTTPException(status_code=500)
    head_of_units = user_repo.get_users_by_user_type(db=db, user_type_id=user_type.id)

    # head_of_units[0].head_of_unit.jurisdiction.courts[0].commissioner_profile[0].user
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Head Of Units retrieved successfully",
        data=[
            HeadOfUnitInResponse(
                id=head_of_unit.id,
                first_name=head_of_unit.first_name,
                last_name=head_of_unit.last_name,
                email=head_of_unit.email,
                date_created=head_of_unit.CreatedAt,
                user_type=UserTypeInDB(
                    id=head_of_unit.user_type.id,
                    name=head_of_unit.user_type.name,
                ),
                verify_token="",
                is_active=head_of_unit.is_active,
                jurisdiction=CourtSystemInDB(
                    name=head_of_unit.head_of_unit.jurisdiction.name,
                    id=head_of_unit.head_of_unit.jurisdiction.id,
                ),
                courts=[
                    CourtSystemInDB(name=court.name, id=court.id)
                    for court in head_of_unit.head_of_unit.jurisdiction.courts
                ],
                commissioners=[
                    UserInResponse(
                        id=commissioner.id,
                        first_name=commissioner.first_name,
                        last_name=commissioner.last_name,
                        email=commissioner.email,
                        user_type=UserTypeInDB(
                            id=commissioner.user_type.id,
                            name=commissioner.user_type.name,
                        ),
                        verify_token="",
                        is_active=commissioner.is_active,
                    )
                    for head_of_unit in head_of_units
                    for court in head_of_unit.head_of_unit.jurisdiction.courts
                    for commissioner_profile in court.commissioner_profile
                    for commissioner in [commissioner_profile.user]
                ],
            )
            for head_of_unit in head_of_units
        ],
    )


@router.get(
    "/general_users",
    # response_model=GenericResponse[List[PublicInResponse]]
)
async def get_users(db: Session = Depends(get_db)):
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

    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"Users information retrieved successfully.",
        data=response,
    )


@router.post("/invite_personel")
async def invite_users(
    users: List[InviteOperationsForm],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_currently_authenticated_user),
    db: Session = Depends(get_db),
):
    for user in users:
        await process_user_invite(user, current_user, db, background_tasks)

    return create_response(
        status_code=status.HTTP_200_OK,
        message="Users invited successfully.",
    )


@router.get(
    "/get_commissioners",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[List[CommissionerInResponse]],
    dependencies=[Depends(admin_permission_dependency)],
)
async def get_commissioners(
    db: Session = Depends(get_db),
):
    results = []

    user_type = user_type_repo.get_by_name(db=db, name=settings.COMMISSIONER_USER_TYPE)
    if user_type is None:
        raise HTTPException(status_code=500)
    commissioners = user_repo.get_users_by_user_type(db, user_type_id=user_type.id)

    for commissioner in commissioners:
        attested_documents = await document_collection.find(
            {"commissioner_id": commissioner.id}
        ).to_list(length=1000)
        documents_serialized = [
            SlimDocumentInResponse(
                id=str(document["_id"]),
                name=document.get("name", ""),
                attested_date=document.get("attestation_date", ""),
                created_at=document.get("created_at", ""),
                status=document.get("status", ""),
            )
            for document in attested_documents
        ]
        fullcommissioner = CommissionerInResponse(
            id=commissioner.id,
            first_name=commissioner.first_name,
            user_type=UserTypeInDB(
                id=commissioner.user_type.id, name=commissioner.user_type.name
            ),
            verify_token="some_verify_token",
            last_name=commissioner.last_name,
            email=commissioner.email,
            court=CourtSystemInDB(
                id=commissioner.commissioner_profile.court.id,
                name=commissioner.commissioner_profile.court.name,
            ),
            is_active=commissioner.is_active,
            attested_documents=documents_serialized,
            date_created=commissioner.CreatedAt,
        )
        results.append(fullcommissioner)
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Commissioners retireved successfully",
        data=results,
    )


# @router.get(
#     "/{commissioner_id}",
#     status_code=status.HTTP_200_OK,
#     dependencies=[Depends(admin_permission_dependency)],
#     response_model=GenericResponse[FullCommissionerInResponse],
# )
# def get_commissioner(commissioner_id: str, db: Session = Depends(get_db)):
#     db_commissioner = user_repo.get(db=db, id=commissioner_id)
#     if (
#         db_commissioner is None
#         or db_commissioner.user_type.name != settings.COMMISSIONER_USER_TYPE
#     ):
#         raise HTTPException(status_code=404, detail="Commissioner not found.")

#     return create_response(
#         status_code=status.HTTP_200_OK,
#         message="Profile retrieved successfully",
#         data=FullCommissionerInResponse(
#             first_name=db_commissioner.first_name,
#             last_name=db_commissioner.last_name,
#             email=db_commissioner.email,
#             is_active=db_commissioner.is_active,
#             court=CourtSystemInDB(
#                 id=db_commissioner.commissioner_profile.court.id,
#                 name=db_commissioner.commissioner_profile.court.name,
#             ),
#         ),
#     )


@router.get(
    "/accept-invite/{token}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[AcceptedInviteResponse],
)
async def accept_invite(token: str, db: Session = Depends(get_db)):

    # invite_info = get_token_details(token, get_all_details_from_token)

    try:

        invite_info = get_user_id_from_token(token)
        invite_id = invite_info.get("id")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token validation error: {str(e)}")

    db_invite: UserInvite = user_invite_repo.get(db, id=invite_id)
    if not db_invite:
        raise HTTPException(status_code=404, detail="Invite not found or invalid.")
    if db_invite.is_accepted:
        raise HTTPException(
            status_code=400, detail="This invitation has already been accepted."
        )

    user_invite_repo.mark_invite_as_accepted(db, db_obj=db_invite)

    return create_response(
        message="Invite accepted successfully",
        status_code=status.HTTP_200_OK,
        data=AcceptedInviteResponse(
            first_name=db_invite.first_name,
            last_name=db_invite.last_name,
            email=db_invite.email,
            is_accepted=db_invite.is_accepted,
            invite_id=db_invite.id,
            user_type=UserTypeInDB(
                id=db_invite.user_type.id, name=db_invite.user_type.name
            ),
        ),
    )


# @router.get(
#     "/",
#     dependencies=[Depends(admin_permission_dependency)],
#     response_model=GenericResponse[List[UserInResponse]],
# )
# def get_all_admins(db: Session = Depends(get_db)):
#     """Get all admin users"""
#     user_type = user_type_repo.get_by_name(db, name=settings.ADMIN_USER_TYPE)
#     admins = user_repo.get_users_by_user_type(db, user_type.id)
#     return create_response(
#         message="Admins retrieved successfully",
#         status_code=status.HTTP_200_OK,
#         data=[
#             UserInResponse(
#                 id=admin.id,
#                 first_name=admin.first_name,
#                 last_name=admin.last_name,
#                 email=admin.email,
#                 is_active=admin.is_active,
#                 user_type=UserTypeInDB(
#                     id=admin.user_type.id,
#                     name=admin.user_type.name,
#                 ),
#                 verify_token="",
#             )
#             for admin in admins
#         ],
#     )


@router.get(
    "/get_all_admins",
    # dependencies=[Depends(admin_permission_dependency)],
    response_model=GenericResponse[List[AdminInResponse]],
)
async def get_all_admins(db: Session = Depends(get_db)):
    """Get all admin users"""
    user_type = user_type_repo.get_by_name(db, name=settings.ADMIN_USER_TYPE)
    admins = user_repo.get_users_by_user_type(db, user_type_id=user_type.id)
    result = []
    for admin in admins:
        templates_created = await template_collection.find(
            {"created_by_id": admin.id}
        ).to_list(length=1000)
        templates_serialized = [
            SlimTemplateInResponse(
                id=str(template["_id"]),
                name=template.get("name", ""),
                price=template.get("price", 0),
                description=template.get("description", ""),
                category=template.get("category", ""),
            )
            for template in templates_created
        ]
        admin = AdminInResponse(
            id=admin.id,
            date_created=admin.CreatedAt,
            first_name=admin.first_name,
            email=admin.email,
            last_name=admin.last_name,
            is_active=admin.is_active,
            verify_token="",
            user_type=UserTypeInDB(id=admin.user_type.id, name=admin.user_type.name),
            users_invited=[
                UserInResponse(
                    id=user.user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    user_type=UserTypeInDB(
                        id=user.user_type.id, name=user.user_type.name
                    ),
                    email=user.email,
                    is_active=user.user.is_active,
                    verify_token="",
                )
                for user in admin.invited_by
            ],
            templates_created=templates_serialized,
        )
        result.append(admin)

    return create_response(
        message="Admins retrieved successfully",
        status_code=status.HTTP_200_OK,
        data=result,
    )


# @router.get(
#     "/{id}",
#     status_code=status.HTTP_200_OK,
#     dependencies=[Depends(admin_permission_dependency)],
#     response_model=GenericResponse[UserInResponse],
# )
# def get_admin(id: str, db: Session = Depends(get_db)):
#     """Get an admin by ID"""
#     admin = user_repo.get(db, id=id)
#     return UserInResponse(
#         id=admin.id,
#         first_name=admin.first_name,
#         last_name=admin.last_name,
#         email=admin.email,
#         is_active=admin.is_active,
#         user_type=UserTypeInDB(
#             id=admin.user_type.id,
#             name=admin.user_type.name,
#         ),
#         verify_token="",
#     )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponse[UserInResponse],
)
def create_admin(admin_in: OperationsCreateForm, db: Session = Depends(get_db)):
    db_invite = user_invite_repo.get(db, id=admin_in.invite_id)
    if not db_invite:
        raise DoesNotExistException(detail="Invitation does not exist or is invalid.")
    if not db_invite.is_accepted:
        raise HTTPException(
            status_code=403,
            detail="Cannot use un-accepted invites for creating new accounts.",
        )
    if db_invite.user_type.name != settings.ADMIN_USER_TYPE:
        raise UnauthorizedEndpointException(
            detail="You do not have permission to access this endpoint.",
        )
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
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message="Account created successfully",
            data=UserInResponse(
                id=new_admin.id,
                first_name=new_admin.first_name,
                last_name=new_admin.last_name,
                email=new_admin.email,
                verify_token=verify_token,
                user_type=UserTypeInDB(
                    name=new_admin.user_type.name, id=new_admin.user_type.id
                ),
                is_active=new_admin.is_active,
            ),
        )
    except Exception as e:
        logger.error(e)


@router.get(
    "/me",
    dependencies=[Depends(admin_permission_dependency)],
    response_model=GenericResponse[UserInResponse],
)
def retrieve_current_admin(
    db: Session = Depends(get_db),
    current_user=Depends(get_currently_authenticated_user),
) -> UserInResponse:
    """
    This is used to retrieve the currently logged-in admin's profile.
    You need to send a token in and it returns a full profile of the currently logged in user.hur
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


@router.get("/get_all_jurisdictions")
async def get_all_jurisdictions(db: Session = Depends(get_db)):
    jurisdictions = jurisdiction_repo.get_all(db)
    return create_response(
        message="Jurisdictions retrieved Successfully",
        status_code=status.HTTP_200_OK,
        data=[
            SlimJurisdictionInResponse(
                id=jurisdiction.id,
                name=jurisdiction.name,
                courts=len(jurisdiction.courts),
                date_created=jurisdiction.CreatedAt,
            )
            for jurisdiction in jurisdictions
        ],
    )


@router.get("/get_jurisdiction/{jurisdiction_id}")
async def get_jurisdiction(jurisdiction_id: str, db: Session = Depends(get_db)):
    jurisdiction = jurisdiction_repo.get(db, id=jurisdiction_id)
    jurisdiction_documents = []
    if not jurisdiction:
        raise DoesNotExistException(detail="Jurisdiction does not exist")
    for court in jurisdiction.courts:
        document_in = await document_collection.find(
            {
                "court_id": court.id,
                "status": {"$in": ["PAID", "ATTESTED"]},
            }
        ).to_list(length=1000)
        jurisdiction_documents.extend(serialize_mongo_document(document_in))
    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{jurisdiction.name} Retrieved successfully",
        data=JurisdictionInResponse(
            id=jurisdiction.id,
            name=jurisdiction.name,
            date_created=jurisdiction.CreatedAt,
            state=CourtSystemInDB(
                name=jurisdiction.state.name, id=jurisdiction.state.id
            ),
            courts=[
                SlimCourtInResponse(
                    id=court.id,
                    date_created=court.CreatedAt,
                    name=court.name,
                    commissioners=len(court.commissioner_profile),
                    documents=await document_collection.count_documents(
                        {"court_id": court.id}
                    ),
                )
                for court in jurisdiction.courts
            ],
            head_of_unit=(
                SlimUserInResponse(
                    id=jurisdiction.head_of_unit.user.id,
                    first_name=jurisdiction.head_of_unit.user.first_name,
                    last_name=jurisdiction.head_of_unit.user.last_name,
                    email=jurisdiction.head_of_unit.user.email,
                )
                if jurisdiction.head_of_unit
                else None
            ),
            commissioners=[
                SlimUserInResponse(
                    id=commissioner.id,
                    first_name=commissioner.first_name,
                    last_name=commissioner.last_name,
                    email=commissioner.email,
                )
                for court in jurisdiction.courts
                for commissioner_profile in court.commissioner_profile
                for commissioner in [commissioner_profile.user]
            ],
            documents=len(jurisdiction_documents),
        ),
    )


@router.get("/get_court/{court_id}")
async def get_court(court_id: str, db: Session = Depends(get_db)):
    court = court_repo.get(db, id=court_id)
    court_documents = []
    if not court:
        raise DoesNotExistException(detail="Court does not exist")

    document_in = await document_collection.find(
        {
            "court_id": court.id,
            "status": {"$in": ["PAID", "ATTESTED"]},
        }
    ).to_list(length=1000)
    court_documents.extend(serialize_mongo_document(document_in))
    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{court.name} Retrieved successfully",
        data=CourtInResponse(
            id=court.id,
            name=court.name,
            date_created=court.CreatedAt,
            jurisdiction=CourtSystemInDB(
                name=court.jurisdiction.name, id=court.jurisdiction.id
            ),
            commissioners=[
                SlimUserInResponse(
                    id=commissioner.id,
                    first_name=commissioner.first_name,
                    last_name=commissioner.last_name,
                    email=commissioner.email,
                )
                for commissioner_profile in court.commissioner_profile
                for commissioner in [commissioner_profile.user]
            ],
            documents=[
                SlimDocumentInResponse(
                    id=str(document.get("id")),
                    name=document.get("name", ""),
                    price=document.get("price", 0),
                    attestation_date=document.get("attest", ""),
                    created_at=document.get("created_at", ""),
                    status=document.get("status", ""),
                )
                for document in court_documents
            ],
        ),
    )




##############
#################
### AFFIDAVITS ROUTES#####
#########
##########

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


@router.get(
    "/get_templates",
    dependencies=[Depends(admin_permission_dependency)],
    response_model=GenericResponse[List[TemplateBase]],
)
async def get_templates():
    try:
        templates = await template_collection.find().to_list(length=100)
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

@router.get(
    "/get_template/{template_id}",
    response_model=GenericResponse[TemplateBase],
    # dependencies=[Depends(admin_permission_dependency)],
)
async def get_template(template_id: str):
    try:
        # Convert the string ID to ObjectId
        object_id = ObjectId(template_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ID format: {template_id}")

    # Log the ObjectId
    logger.info(f"Fetching template with ID: {object_id}")

    template_obj = await template_collection.find_one({"_id": object_id})

    # Log the result of the query
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
        data=template_obj,
    )




@router.patch(
    "/update_template/{template_id}",
    dependencies=[Depends(admin_permission_dependency)],
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[TemplateBase],
)
async def update_template(
    template_in: TemplateBase,
    current_user: User = Depends(get_currently_authenticated_user),
):
    template_dict = {**template_in.dict(), "updated_at": datetime.utcnow()}
    object_id = ObjectId(template_dict["id"])
    existing_template = await template_collection.find_one({"_id": object_id})

    if not existing_template:

        raise HTTPException(status_code=404, detail="Template does not exist")

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


@router.put(
    "/activate_user/{user_id}",
    dependencies=[Depends(admin_permission_dependency)],
)
def activate_user(user_id: str, db: Session = Depends(get_db)):
    db_user = user_repo.get(db, id=user_id)
    if not db_user:
        raise DoesNotExistException(detail="User does not exist")
    if db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is already active.",
        )
    user_repo.activate(db, db_obj=db_user)

    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{db_user.first_name } {db_user.last_name} activated successfully",
    )


@router.put(
    "/deactivate_user/{user_id}",
    dependencies=[Depends(admin_permission_dependency)],
)
def deactivate_user(user_id: str, db: Session = Depends(get_db)):
    db_user = user_repo.get(db, id=user_id)
    if not db_user:
        raise DoesNotExistException(detail="User does not exist")
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account is already in-active.",
        )
    user_repo.deactivate(db, db_obj=db_user)

    return create_response(
        status_code=status.HTTP_200_OK,
        message=f"{db_user.first_name } {db_user.last_name} de-activated successfully",
    )
