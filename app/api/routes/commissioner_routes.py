from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session
from app.api.dependencies.authentication import (
    get_currently_authenticated_user,
    commissioner_permission_dependency,
)
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    UnauthorizedEndpointException,
)
from app.models.user_model import User
from app.repositories.head_of_unit_repo import head_of_unit_repo
from app.repositories.user_invite_repo import user_invite_repo
from app.repositories.user_repo import user_repo
from app.repositories.user_type_repo import user_type_repo
from app.core.settings.configurations import settings
from app.schemas.court_system_schema import CourtSystemInDB
from app.schemas.user_schema import (
    CommissionerAttestation,
    CommissionerCreate,
    CommissionerProfileBase,
    CommissionerProfileCreate,
    FullCommissionerInResponse,
    FullCommissionerProfile,
    OperationsCreateForm,
    UserCreate,
    UserInResponse,
)
from app.api.dependencies.authentication import (
    admin_and_head_of_unit_permission_dependency,
)
from app.repositories.commissioner_profile_repo import comm_profile_repo
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import GenericResponse, create_response


router = APIRouter()




@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    # response_model=GenericResponse[List[CommissionerProfileBase]],
    dependencies=[Depends(admin_and_head_of_unit_permission_dependency)],
)
def get_commissioners(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    commissioners = []
    if current_user.user_type.name == settings.HEAD_OF_UNIT_USER_TYPE:

        commissioner_profiles = head_of_unit_repo.get_commissioners_under_jurisdiction(
            db, jurisdiction_id=current_user.head_of_unit.jurisdiction_id
        )
        commissioners = [commissioner.user for commissioner in commissioner_profiles]
    else:
        user_type = user_type_repo.get_by_name(
            db=db, name=settings.COMMISSIONER_USER_TYPE
        )
        if user_type is None:
            raise HTTPException(status_code=500)
        commissioners = user_repo.get_users_by_user_type(db, user_type_id=user_type.id)
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Commissioners retireved successfully",
        data=[
            CommissionerProfileBase(
                id=commissioner.id,
                first_name=commissioner.first_name,
                last_name=commissioner.last_name,
                email=commissioner.email,
                court=commissioner.commissioner_profile.court.name,
                is_active=commissioner.is_active,
            )
            for commissioner in commissioners
        ],
    )

@router.get(
    "/{commissioner_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(admin_and_head_of_unit_permission_dependency)],
    response_model=GenericResponse[FullCommissionerInResponse],
)
def get_commissioner(commissioner_id: str, db: Session = Depends(get_db)):
    db_commissioner = user_repo.get(db=db, id=commissioner_id)
    if (
        db_commissioner is None
        or db_commissioner.user_type.name != settings.COMMISSIONER_USER_TYPE
    ):
        raise HTTPException(status_code=404, detail="Commissioner not found.")
    
    return create_response(
        status_code=status.HTTP_200_OK,
        message="Profile retrieved successfully",
        data=FullCommissionerInResponse(
            first_name=db_commissioner.first_name,
            last_name=db_commissioner.last_name,
            email=db_commissioner.email,
            is_active=db_commissioner.is_active,
            court=CourtSystemInDB(
                id=db_commissioner.commissioner_profile.court.id,
                name=db_commissioner.commissioner_profile.court.name,
            ),
        ),
    )



@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_commissioner(
    commissioner_in: OperationsCreateForm,
    db: Session = Depends(get_db),
):
    # Validate the invitation
    db_invite = user_invite_repo.get(db=db, id=commissioner_in.invite_id)
    if not db_invite:
        raise DoesNotExistException(detail="Invitation does not exist or is invalid.")
    if not db_invite.is_accepted:
        raise HTTPException(
            status_code=403,
            detail="Cannot use un-accepted invites for creating new accounts.",
        )

    # Ensure the invite is for a commissioner
    if db_invite.user_type.name != settings.COMMISSIONER_USER_TYPE:
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

    # Create the commissioner
    commissioner_obj = UserCreate(
        first_name=db_invite.first_name,
        last_name=db_invite.last_name,
        user_type_id=db_invite.user_type_id,
        password=commissioner_in.password,
        email=db_invite.email,
    )
    try:
        db_commissioner = user_repo.create(db=db, obj_in=commissioner_obj)
        if db_commissioner:
            commissioner_profile_in = CommissionerProfileCreate(
                commissioner_id=db_commissioner.id,
                court_id=db_invite.court_id,
                created_by_id=db_invite.invited_by_id,
            )
            comm_profile_repo.create(db=db, obj_in=commissioner_profile_in)
        verify_token = user_repo.create_verification_token(
            email=db_commissioner.email, db=db
        )
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
                    name=db_commissioner.user_type.name, id=db_commissioner.user_type.id
                ),
                is_active=db_commissioner.is_active,
            ),
        )
    except Exception as e:
        logger.error(e)




@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(commissioner_permission_dependency)],
    response_model=GenericResponse[FullCommissionerInResponse],
)
def get_current_commissioner(
    current_user=Depends(get_currently_authenticated_user),
):
    """
    This is used to retrieve the currently logged-in commissioner's profile.
    You need to send a token in and it returns a full profile of the currently logged in commissioner.
    You send the token in as a header of the form \n
    <b>Authorization</b> : 'Token <b> {JWT} </b>'
    """

    return create_response(
        status_code=status.HTTP_200_OK,
        message="Profile retrieved successfully",
        data=FullCommissionerProfile(
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            email=current_user.email,
            attestation=CommissionerAttestation(
                stamp=(
                    current_user.commissioner_profile.stamp
                    if current_user.commissioner_profile.stamp
                    else ""
                ),
                signature=(
                    current_user.commissioner_profile.signature
                    if current_user.commissioner_profile.signature
                    else ""
                ),
            ),
            is_active=current_user.is_active,
            court=CourtSystemInDB(
                id=current_user.commissioner_profile.court.id,
                name=current_user.commissioner_profile.court.name,
            ),
            user_type=UserTypeInDB(
                id=current_user.user_type.id, name=current_user.user_type.name
            ),
        ),
    )


@router.put(
    "/update_attestation", dependencies=[Depends(commissioner_permission_dependency)]
)
def create_attestation(
    db: Session = Depends(get_db), user=Depends(get_currently_authenticated_user)
):
    return {"notice": "Attestations are now being automatically created."}


@router.put(
    "/activate_commissioner/{commissioner_id}",
    dependencies=[Depends(admin_and_head_of_unit_permission_dependency)]
)
def activate_user(
    commissioner_id:str,
    db:Session = Depends(get_db)
    
    
):
    commissioner = user_repo.get(db, id=commissioner_id)
    if not commissioner:
        raise DoesNotExistException(detail="Commissioner does not exist")
    if commissioner.is_active:
        raise  HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account is already active.")
    user_repo.activate(db, user=commissioner)

    return  {"message":"The account has been reactivated"}