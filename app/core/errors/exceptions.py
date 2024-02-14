from typing import Any, Optional
from app.core.errors import error_strings
from fastapi import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_409_CONFLICT,
)


class ServerException(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_strings.SERVER_ERROR,
        )


class IncorrectLoginException(HTTPException):
    def __init__(
        self,
        status_code=HTTP_401_UNAUTHORIZED,
        detail=error_strings.INCORRECT_LOGIN_INPUT,
        headers=None,
    ):
        super().__init__(
            status_code,
            detail=detail,
            headers=headers,
        )


class DisallowedLoginException(HTTPException):
    def __init__(
        self,
        status_code=HTTP_401_UNAUTHORIZED,
        detail=error_strings.UNVERIFIED_USER_ERROR,
        headers=None,
    ):
        super().__init__(
            status_code,
            detail=detail,
            headers=headers,
        )




class AlreadyExistsException(HTTPException):
    def __init__(
        self,
        status_code=HTTP_409_CONFLICT,
        detail=error_strings.ALREADY_EXISTS,
        headers=None,
        entity_name="",
    ):
        super().__init__(
            status_code,
            detail=detail.format(entity_name),
            headers=headers,
        )


class InvalidTokenException(HTTPException):
    def __init__(
        self,
        status_code=HTTP_403_FORBIDDEN,
        detail=error_strings.MALFORMED_PAYLOAD,
        headers=None,
    ):
        super().__init__(
            status_code,
            detail=detail,
            headers=headers,
        )


class ObjectNotFoundException(HTTPException):
    def __init__(
        self,
        status_code=HTTP_404_NOT_FOUND,
        detail=error_strings.NOT_FOUND,
        headers=None,
    ):
        super().__init__(
            status_code,
            detail=detail,
            headers=headers,
        )


class UnauthorizedEndpointException(HTTPException):
    def __init__(
        self, status_code=HTTP_403_FORBIDDEN, detail=error_strings.UNAUTHORIZED_ACTION
    ):
        super().__init__(
            status_code=status_code,
            detail=detail,
        )




class DoesNotExistException(HTTPException):
    def __init__(
        self,
        status_code=HTTP_404_NOT_FOUND,
        detail=error_strings.DOES_NOT_EXIST,
        headers=None,
        entity_name="",
    ):
        super().__init__(
            status_code,
            detail=detail.format(entity_name),
            headers=headers,
        )
        


