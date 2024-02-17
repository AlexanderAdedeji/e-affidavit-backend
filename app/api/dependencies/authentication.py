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
# REFRESH_HEADER_KEY = settings.REFRESH_HEADER_KEY
# REFRESH_EXP_MINS = settings.REFRESH_EXP_MINS
ADMIN_USER_TYPE = settings.ADMIN_USER_TYPE
SUPERUSER_USER_TYPE = settings.SUPERUSER_USER_TYPE
HEAD_OF_UNIT_USER_TYPE = settings.HEAD_OF_UNIT_USER_TYPE
COMMISSIONER_USER_TYPE = settings.COMMISSIONER_USER_TYPE


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
    user = user_repo.get(db, id=token_details["id"])
    check_if_user_is_valid(user)
    return user


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
    allowed_user_types=[ADMIN_USER_TYPE]
)

head_of_unit_permission_dependency = PermissionChecker(
    allowed_user_types=[HEAD_OF_UNIT_USER_TYPE]
)


admin_and_head_of_unit_permission_dependency = PermissionChecker(
    allowed_user_types=[HEAD_OF_UNIT_USER_TYPE, ADMIN_USER_TYPE]
)

commissioner_permission_dependency = PermissionChecker(
    allowed_user_types=[COMMISSIONER_USER_TYPE]
)


superuser_permission_dependency = PermissionChecker(
    allowed_user_types=[SUPERUSER_USER_TYPE]
)
