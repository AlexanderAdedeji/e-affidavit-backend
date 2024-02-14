from app.core.services.jwt import get_user_id_from_token, get_all_details_from_token
from typing import Optional, List
from datetime import timedelta
from fastapi import Depends, Security, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import APIKeyHeader as DefaultAPIKeyHeader
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.models.user_type_model import UserType
from app.schemas.user_schema import UserBase
from starlette import requests, status
from app.api.dependencies.db import get_db
from app.core.errors.error_strings import (
    AUTHENTICATION_REQUIRED,
    INACTIVE_USER_ERROR,
    MALFORMED_PAYLOAD,
    WRONG_TOKEN_PREFIX,
    UNAUTHORIZED_ACTION,
)
from app.repositories.user_repo import user_repo
from app.core.errors.exceptions import (
    DisallowedLoginException,
    InvalidTokenException,
)
from app.models.user_model import User
from loguru import logger
from app.core.settings.configurations import settings
from app.schemas.user_type_schema import UserTypeBase


JWT_TOKEN_PREFIX = settings.JWT_TOKEN_PREFIX
HEADER_KEY = settings.HEADER_KEY
REFRESH_HEADER_KEY = settings.REFRESH_HEADER_KEY
REFRESH_EXP_MINS = settings.REFRESH_EXP_MINS
ADMIN_USER_TYPE = settings.ADMIN
SUPERUSER_USER_TYPE = settings.SUPERUSER
HEAD_OF_UNIT_USER_TYPE = settings.HEAD_OF_UNIT
COMMISSIONER = settings.COMMISSIONER


class JWTHEADER(DefaultAPIKeyHeader):
    async def __call__(
        _,
        request: requests.Request,
    ) -> Optional[str]:
        try:
            return await super().__call__(request)
        except StarletteHTTPException as original_auth_exc:
            raise HTTPException(
                status_code=original_auth_exc.status_code,
                detail=original_auth_exc.detail or AUTHENTICATION_REQUIRED,
            )


def _extract_jwt_from_header(
    authorization_header: str = Security(JWTHEADER(name=HEADER_KEY)),
):
    try:
        token_prefix, token = authorization_header.split(" ")
    except ValueError:
        raise InvalidTokenException(detail=WRONG_TOKEN_PREFIX)
    if token_prefix != JWT_TOKEN_PREFIX:
        raise InvalidTokenException(detail=WRONG_TOKEN_PREFIX)
    return token


def _extract_refresh_jwt_from_header(
    authorization_header: str = Security(JWTHEADER(name=HEADER_KEY)),
):
    try:
        token_prefix, token = authorization_header.split(" ")
    except ValueError:
        raise InvalidTokenException(detail=WRONG_TOKEN_PREFIX)
    if token_prefix != JWT_TOKEN_PREFIX:
        raise InvalidTokenException(detail=WRONG_TOKEN_PREFIX)
    return token


def check_if_user_is_valid(user: User):
    if not user:
        raise InvalidTokenException(detail=MALFORMED_PAYLOAD)
    if not user.is_active:
        raise DisallowedLoginException(detail=INACTIVE_USER_ERROR)


def get_token_details(token: str, method):
    try:
        logger.debug(f"Token: {token}")
        token_details = method(token)
        logger.debug(f"Token Details: {token_details}")
        return token_details
    except ValueError:
        raise InvalidTokenException(detail=MALFORMED_PAYLOAD)


def get_currently_authenticated_user(
    *,
    db: Session = Depends(get_db),
    token: str = Depends(_extract_jwt_from_header),
) -> User:
    token_details = get_token_details(token, get_user_id_from_token)
    user = user_repo.get(db, id=token_details["user_id"])
    check_if_user_is_valid(user)
    return user


# def get_currently_authenticated_associate(
#     *,
#     db: Session = Depends(get_db),
#     token: str = Depends(_extract_jwt_from_header),
# ):
#     token_details = get_token_details(token, get_associate_id_from_token)
#     associates = associate_repo.get_associate_role(
#         db,
#         organisation_id=token_details["organisation_id"],
#         user_id=token_details["user_id"],
#     )
#     return associates


# def get_refresh_token(
#     *,
#     db: Session = Depends(get_db),
#     token: str = Depends(_extract_refresh_jwt_from_header),
# ):
#     token_details = get_token_details(token, get_all_details_from_token)
#     if "organisation_id" not in token_details:
#         user = user_repo.get(db, id=token_details["user_id"])
#         check_if_user_is_valid(user)
#         token = user.generate_jwt()
#         refresh_token = user.generate_jwt(
#             expires_delta=timedelta(minutes=REFRESH_EXP_MINS)
#         )
#         return {
#             "id": user.id,
#             "first_name": user.first_name,
#             "last_name": user.last_name,
#             "token": token,
#             "refresh_token": refresh_token,
#         }
#     else:
#         associate = associate_repo.get_associate_role(
#             db,
#             organisation_id=token_details["organisation_id"],
#             user_id=token_details["user_id"],
#         )
#         token = associate.generate_jwt()
#         refresh_token = associate.generate_refresh_jwt(
#             expires_delta=timedelta(minutes=REFRESH_EXP_MINS)
#         )
#         return {
#             "id": associate.organisation.id,
#             "name": associate.organisation.name,
#             "logo": associate.organisation.logo,
#             "role": associate.role,
#             "token": associate.generate_jwt(),
#             "refresh_token": associate.generate_refresh_jwt(),
#         }


# class PermissionChecker:
#     def __init__(self, *, allowed_associate_roles: List[str]):
#         self.allowed_associate_roles = allowed_associate_roles

#     def __call__(self, associate=Depends(get_currently_authenticated_associate)):
#         current_associate_role = associate.role
#         logger.debug(f"Current Associate Role: {current_associate_role}")
#         if current_associate_role not in self.allowed_associate_roles:
#             logger.debug(
#                 f"User with role {current_associate_role} not in  {self.allowed_associate_roles}"
#             )
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN, detail=UNAUTHORIZED_ACTION
#             )

#     def send_invite_permission(
#         self, associate=Depends(get_currently_authenticated_associate)
#     ):
#         return associate


# manager_and_owner_permission_dependency = PermissionChecker(
#     allowed_associate_roles=[MANAGER_ASSOCIATE, OWNER_ASSOCIATE]
# )
# all_permissions_dependency = PermissionChecker(
#     allowed_associate_roles=[
#         MANAGER_ASSOCIATE,
#         OWNER_ASSOCIATE,
#         MEMBER_ASSOCIATE,
#         CLIENT_ASSOCIATE,
#     ]
# )
class PermissionChecker:
    def __init__(self, *, allowed_user_types: List[str]):
        self.allowed_user_types = allowed_user_types + [SUPERUSER_USER_TYPE]

    def __call__(self, user: User = Depends(get_currently_authenticated_user)):
        current_user_type: UserType = user.user_type
        if current_user_type.name not in self.allowed_user_types:
            logger.debug(
                f"User type '{current_user_type.name}' not allowed. Permitted types: {self.allowed_user_types}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=UNAUTHORIZED_ACTION
            )


admin_permission_dependency = PermissionChecker(
    allowed_user_types=[SUPERUSER_USER_TYPE, ADMIN_USER_TYPE]
)

head_of_unit_permission_dependency = PermissionChecker(
    allowed_user_types=[HEAD_OF_UNIT_USER_TYPE]
)


admin_and_head_of_unit_permission_dependency = PermissionChecker(
    allowed_user_types=[HEAD_OF_UNIT_USER_TYPE, ADMIN_USER_TYPE]
)

commissioner_permission_dependency = PermissionChecker(
    allowed_user_types=[HEAD_OF_UNIT_USER_TYPE]
)


superuser_permission_dependency = PermissionChecker(
    allowed_user_types=[SUPERUSER_USER_TYPE]
)
