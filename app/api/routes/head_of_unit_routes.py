from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session
from app.api.dependencies.authentication import (
    get_currently_authenticated_user,
    head_of_unit_permission_dependency,
    admin_permission_dependency,
)
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    UnauthorizedEndpointException,
)
from app.repositories.user_invite_repo import user_invite_repo
from app.repositories.user_repo import user_repo
from app.repositories.head_of_unit_repo import head_of_unit_repo
from app.repositories.user_type_repo import user_type_repo
from app.core.settings.configurations import settings
from app.schemas.court_system_schema import CourtSystemInDB
from app.schemas.user_schema import (
    CommissionerCreate,
    CommissionerProfileBase,
    FullCommissionerInResponse,
    FullHeadOfUniteInResponse,
    HeadOfUnitBase,
    HeadOfUnitCreate,
    OperationsCreateForm,
    UserCreate,
    UserInResponse,
)
from app.repositories.commissioner_profile_repo import comm_profile_repo
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import create_response, GenericResponse


router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponse[UserInResponse],
)
async def create_head_of_unit(
    head_of_unit_in: OperationsCreateForm,
    db: Session = Depends(get_db),
):
    # Validate the invitation
    db_invite = user_invite_repo.get(db=db, id=head_of_unit_in.invite_id)
    if not db_invite:
        raise DoesNotExistException(detail="Invitation does not exist or is invalid.")
    if not db_invite.is_accepted:
        raise HTTPException(
            status_code=403,
            detail="Cannot use un-accepted invites for creating new accounts.",
        )

    # Ensure the invite is for a commissioner
    if db_invite.user_type.name != settings.HEAD_OF_UNIT_USER_TYPE:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this endpoint.",
        )

    # Check if the email is already used
    if user_repo.get_by_email(db=db, email=db_invite.email):
        raise HTTPException(
            status_code=409,
            detail=f"User with email {db_invite.email} already exists.",
        )

    # Create the Head of unit
    head_of_unit_obj = UserCreate(
        first_name=db_invite.first_name,
        last_name=db_invite.last_name,
        user_type_id=db_invite.user_type_id,
        password=head_of_unit_in.password,
        email=db_invite.email,
    )
    try:
        db_head_of_unit = user_repo.create(db=db, obj_in=head_of_unit_obj)
        if db_head_of_unit:
            head_of_unit_in = HeadOfUnitBase(
                head_of_unit_id=db_head_of_unit.id,
                jurisdiction_id=db_invite.jurisdiction_id,
                created_by_id=db_invite.invited_by_id,
            )
            head_of_unit_repo.create(db=db, obj_in=head_of_unit_in)
        verify_token = user_repo.create_verification_token(
            email=db_head_of_unit.email, db=db
        )
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message="Account created successfully",
            data=UserInResponse(
                id=db_head_of_unit.id,
                first_name=db_head_of_unit.first_name,
                last_name=db_head_of_unit.last_name,
                email=db_head_of_unit.email,
                verify_token=verify_token,
                user_type=UserTypeInDB(
                    name=db_head_of_unit.user_type.name, id=db_head_of_unit.user_type.id
                ),
                      is_active=db_head_of_unit.is_active,
            ),
        )
    except Exception as e:
        logger.error(e)


@router.get("/me", dependencies=[Depends(head_of_unit_permission_dependency)])
def retrieve_current_unit_head(
    db: Session = Depends(get_db), user=Depends(get_currently_authenticated_user)
):
    return user_repo.get(db, id=user.id)



@router.get("/{head_of_unit_id}", dependencies=[Depends(admin_permission_dependency)])
def get_unit_head(head_of_unit_id: str, db: Session = Depends(get_db)):
    db_head_of_unit = user_repo.get(db=db, id=head_of_unit_id)
    if (
        db_head_of_unit is None
        or db_head_of_unit.user_type.name != settings.HEAD_OF_UNIT_USER_TYPE
    ):
        raise HTTPException(status_code=404, detail="Head Of Unit not found.")
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Profile retrieved successfully",
        data=FullHeadOfUniteInResponse(
            first_name=db_head_of_unit.first_name,
            last_name=db_head_of_unit.last_name,
            email=db_head_of_unit.email,
            is_active=db_head_of_unit.is_active,
            jurisdiction=CourtSystemInDB(
                id=db_head_of_unit.jurisdiction.id,
                name=db_head_of_unit.jurisdiction.name,
            ),
            user_type=UserTypeInDB(
                id=db_head_of_unit.user_type.id, name=db_head_of_unit.user_type.name
            ),
        ),
    )


@router.get("/", dependencies=[Depends(admin_permission_dependency)])
def get_unit_heads(db: Session = Depends(get_db)):
    user_type = user_type_repo.get_by_name(db=db, name=settings.HEAD_OF_UNIT_USER_TYPE)
    if user_type is None:
        raise HTTPException(status_code=500)
    head_of_units = user_repo.get_users_by_user_type(db=db, user_type_id=user_type.id)
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Head Of Units retrieved successfully",
        data=[
            UserInResponse(
                id= head_of_unit.id,
                first_name=head_of_unit.first_name,
                last_name=head_of_unit.last_name,
                email=head_of_unit.email,
                user_type=UserTypeInDB(
                    id=head_of_unit.user_type.id, name=head_of_unit.user_type.name
                ),
                verify_token="",
                is_active=head_of_unit.is_active,
            )
            for head_of_unit in head_of_units
        ],
    )


