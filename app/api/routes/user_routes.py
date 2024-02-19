from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from loguru import logger
from sqlalchemy.orm import Session
from app.api.dependencies.authentication import get_currently_authenticated_user
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import AlreadyExistsException, DoesNotExistException
from app.models.user_model import User
from app.repositories.user_repo import user_repo
from app.repositories.user_type_repo import user_type_repo
from app.schemas.user_schema import (
    UserCreate,
    UserCreateForm,
    UserInResponse,
    UserWithToken,
)
from app.core.settings.configurations import settings
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import GenericResponse


router = APIRouter()


@router.post(
    "/user",
    #  response_model=GenericResponse[UserInResponse]
)
def create_user(user_in: UserCreateForm, db: Session = Depends(get_db)):
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
    except IntegrityError as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the user.",
        )

    return UserInResponse(
        id=new_user.id,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        email=new_user.email,
        verify_token=verify_token,
        user_type=UserTypeInDB(name=user_type.name, id=user_type.id),
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
