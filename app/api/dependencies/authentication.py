from starlette import requests, status
from loguru import logger
from app.core.settings.configurations import settings
from app.schemas.user_type_schema import UserTypeBase


from app.core.services.jwt import jwt_service
from typing import Optional, List
from fastapi import Depends, Security, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import APIKeyHeader as DefaultAPIKeyHeader
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.models.user_type_model import UserType
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
from app.core.settings.configurations import settings

JWT_TOKEN_PREFIX = settings.JWT_TOKEN_PREFIX
HEADER_KEY = settings.HEADER_KEY
ADMIN_USER_TYPE = settings.ADMIN_USER_TYPE
SUPERUSER_USER_TYPE = settings.SUPERUSER_USER_TYPE
HEAD_OF_UNIT_USER_TYPE = settings.HEAD_OF_UNIT_USER_TYPE
COMMISSIONER_USER_TYPE = settings.COMMISSIONER_USER_TYPE
PUBLIC_USER_TYPE = settings.PUBLIC_USER_TYPE


class JWTHEADER(DefaultAPIKeyHeader):
    async def __call__(
        self,
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
) -> str:
    try:
        token_prefix, token = authorization_header.split(" ")
        if token_prefix != JWT_TOKEN_PREFIX:
            raise InvalidTokenException(detail=WRONG_TOKEN_PREFIX)
        return token
    except ValueError:
        raise InvalidTokenException(detail=MALFORMED_PAYLOAD)


def check_if_user_is_valid(user: Optional[User]) -> None:
    if not user:
        raise InvalidTokenException(detail=MALFORMED_PAYLOAD)
    if not user.is_active:
        raise DisallowedLoginException(detail=INACTIVE_USER_ERROR)


def get_token_details(token: str, method) -> dict:
    try:
        logger.debug(f"Token: {token}")
        token_details = method(token)
        logger.debug(f"Token Details: {token_details}")
        return token_details
    except (ValueError, KeyError) as e:
        logger.error(f"Error decoding token: {e}")
        raise InvalidTokenException(detail=MALFORMED_PAYLOAD)


def get_currently_authenticated_user(
    *,
    db: Session = Depends(get_db),
    token: str = Depends(_extract_jwt_from_header),
) -> User:
    token_details = get_token_details(token, jwt_service.get_user_id_from_token)
    user = user_repo.get(db, id=token_details.get("id"))
    check_if_user_is_valid(user)
    return user


class PermissionChecker:
    def __init__(
        self, *, allowed_user_types: List[str], include_superuser: bool = True
    ):
        self.allowed_user_types = allowed_user_types
        if include_superuser:
            self.allowed_user_types.append(SUPERUSER_USER_TYPE)
        logger.info(f"Allowed user types for permission: {self.allowed_user_types}")

    def __call__(self, user: User = Depends(get_currently_authenticated_user)) -> None:
        if user.user_type.name not in self.allowed_user_types:
            logger.warning(
                f"User type '{user.user_type.name}' not allowed. Permitted types: {self.allowed_user_types}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=UNAUTHORIZED_ACTION
            )


admin_permission_dependency = PermissionChecker(allowed_user_types=[ADMIN_USER_TYPE])
head_of_unit_permission_dependency = PermissionChecker(
    allowed_user_types=[HEAD_OF_UNIT_USER_TYPE]
)
admin_and_head_of_unit_permission_dependency = PermissionChecker(
    allowed_user_types=[HEAD_OF_UNIT_USER_TYPE, ADMIN_USER_TYPE]
)
commissioner_permission_dependency = PermissionChecker(
    allowed_user_types=[COMMISSIONER_USER_TYPE]
)
authenticated_user_dependencies = PermissionChecker(
    allowed_user_types=[
        COMMISSIONER_USER_TYPE,
        ADMIN_USER_TYPE,
        HEAD_OF_UNIT_USER_TYPE,
        PUBLIC_USER_TYPE,
    ]
)
superuser_permission_dependency = PermissionChecker(
    allowed_user_types=[SUPERUSER_USER_TYPE], include_superuser=False
)
