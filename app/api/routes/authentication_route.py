from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies.db import get_db
from app.core.errors import error_strings
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DisallowedLoginException,
    DoesNotExistException,
    IncorrectLoginException,
)
from app.repositories.user_repo import user_repo

from app.schemas.user_schema import UserCreate, UserInLogin, UserWithToken
from app.schemas.user_type_schema import UserTypeInDB


router = APIRouter()


def check_unique_user(db: Session, user_in: UserCreate):
    user_with_same_email = user_repo.get_by_email(db, email=user_in.email)
    if user_with_same_email:
        raise AlreadyExistsException(
            entity_name="user with email {}".format(user_in.email)
        )


def check_if_user_exist(db: Session, user_in: UserCreate):
    user_exist = user_repo.get_by_email(db, email=user_in.email)
    if not user_exist:
        raise DoesNotExistException(entity_name="user not found")
    return user_exist


@router.post("/login")
def login(user_login: UserInLogin, db: Session = Depends(get_db)):
    user = check_if_user_exist(db, user_in=user_login)

    if user is None or not user.verify_password(user_login.password):
        raise IncorrectLoginException()
    if not user.is_active:
        raise DisallowedLoginException(detail=error_strings.INACTIVE_USER_ERROR)

    token = user.generate_jwt()
    return UserWithToken(
        email=user.email,
        token=token,
        user_type=UserTypeInDB(id=user.user_type_id, name=user.user_type.name),
    )


@router.put("/verify")
def verify_account(
    verification_code: str, db: Session = Depends(get_db)):
    decoded_token = {"user_id": "1"}
    user = user.get