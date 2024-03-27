from typing import List
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from app.core.services.invitation import process_user_invite
from app.schemas.affidavit_schema import (
    SlimTemplateInResponse,
    TemplateContent,
    TemplateInResponse,
    template_individual_serializer,
    template_list_serialiser,
)
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
from app.schemas.court_system_schema import CourtSystemInDB
from app.schemas.email_schema import OperationsInviteTemplateVariables
from app.schemas.user_schema import (
    AcceptedInviteResponse,
    AdminInResponse,
    CreateInvite,
    FullCommissionerInResponse,
    InviteOperationsForm,
    OperationsCreateForm,
    UserCreate,
    UserInResponse,
)
from app.api.dependencies.authentication import get_currently_authenticated_user
from app.core.services.email import email_service
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import create_response, GenericResponse
from app.database.sessions.mongo_client import template_collection

router = APIRouter()


@router.get("/get_dashboard_stats", dependencies=[Depends(admin_permission_dependency)])
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    This endpoint returns the number of users and invites in the system."""
    total_affidavits = 10
    total_users = 10
    total_commissioner = 10
    total_revenue = 10

    return create_response(
        status_code=status.HTTP_200_OK,
        message="Dashboard Stats fetched successfully.",
        data=AdminDashboardStat(
            total_affidavits=total_affidavits,
            total_users=total_users,
            total_commissioners=total_commissioner,
            total_revenue=total_revenue,
        ),
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
        data=result
    )


@router.get(
    "/{id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(admin_permission_dependency)],
    response_model=GenericResponse[UserInResponse],
)
def get_admin(id: str, db: Session = Depends(get_db)):
    """Get an admin by ID"""
    admin = user_repo.get(db, id=id)
    return UserInResponse(
        id=admin.id,
        first_name=admin.first_name,
        last_name=admin.last_name,
        email=admin.email,
        is_active=admin.is_active,
        user_type=UserTypeInDB(
            id=admin.user_type.id,
            name=admin.user_type.name,
        ),
        verify_token="",
    )


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
