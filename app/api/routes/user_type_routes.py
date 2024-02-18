from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.exc import IntegrityError
from starlette import status
from sqlalchemy.orm import Session
from app.api.dependencies.db import get_db
from app.core.errors import error_strings
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    ObjectNotFoundException,
    ServerException,
)
from app.models.user_model import User
from app.repositories.user_type_repo import user_type_repo

from app.api.dependencies.authentication import (
    admin_permission_dependency,
    get_currently_authenticated_user,
)
from app.schemas.user_schema import UserInResponse
from app.schemas.user_type_schema import UserTypeBase, UserTypeCreate, UserTypeInDB
from app.models.user_type_model import UserType
from commonLib.response.response_schema import GenericResponse, create_response
from app.core.settings.configurations import settings

router = APIRouter()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[List[UserTypeInDB]],
    dependencies=[Depends(admin_permission_dependency)],
)
def get_all_user_types(db: Session = Depends(get_db)):
    """
    This is used to retrieve the list of all user types in the application
    You need to be an admin to use this endpoint.
    You send the token in as a header of the form \n
    <b>Authorization</b> : 'Token <b> {JWT} </b>'
    """
    user_types = user_type_repo.get_all(db)
    response = dict(
        data=[
            UserTypeInDB(id=user_type.id, name=user_type.name)
            for user_type in user_types
            if user_type.name.lower() != settings.SUPERUSER_USER_TYPE.lower()
        ],
        message="successful",
        status_code=status.HTTP_200_OK,
    )
    return response


@router.get(
    "/{user_type_id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[UserTypeBase],
    dependencies=[Depends(admin_permission_dependency)],
)
async def get_single_user_type(*, user_type_id: str, db: Session = Depends(get_db)):
    user_type = user_type_repo.get(db, id)
    return create_response(
        status_code=status.HTTP_200_OK,
        message="usertype found",
        data=UserType(id=user_type.id, name=user_type.name),
    )


@router.delete(
    "/{user_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(admin_permission_dependency)],
)
async def delete_user_type(*, user_type_id: str, db: Session = Depends(get_db)):
    if not user_type_repo.exist(db, user_type_id):
        raise DoesNotExistException(detail="No such usertype exists.")
    else:
        user_type_repo.remove(db=db, id=user_type_id)
        return create_response(
            status_code=status.HTTP_204_NO_CONTENT,
            message="User type deleted successfully.",
        )


@router.put(
    "/{user_type_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenericResponse[UserTypeInDB],
    dependencies=[Depends(admin_permission_dependency)],
)
async def edit_user_type(
    *, user_type_id: str, user_type_in: UserTypeCreate, db: Session = Depends(get_db)
):
    try:
        user_type_exist = user_type_repo.get(db=db, id=user_type_id)

        if not user_type_exist:
            raise DoesNotExistException(detail="No such usertype exists.")

        exists = bool(user_type_repo.get_by_name(db, name=user_type_in.name))

        if exists:
            raise AlreadyExistsException(
                detail=error_strings.ALREADY_EXISTS.format(
                    "user type with name " + user_type_in.name
                )
            )
        user_type_in.name = user_type_in.name.upper()
        updated_user_type = user_type_repo.update(
            db=db, obj_in=user_type_in, db_obj=user_type_exist
        )

        return create_response(
            status_code=status.HTTP_204_NO_CONTENT,
            message="User type edited successfully.",
            data=UserTypeInDB(id=updated_user_type.id, name=updated_user_type.name),
        )

    except Exception as e:

        logger.error("Error in update operation", e)
        raise ServerException()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponse[UserTypeBase],
    # dependencies=[Depends(admin_permission_dependency)],
)
def create_user_type(
    user_type_in: UserTypeCreate,
    db: Session = Depends(get_db),
) -> UserTypeBase:
    """
    This is used to create a new user type in the application
    You need to be an admin to use this endpoint.
    You send the token in as a header of the form \n
    <b>Authorization</b> : 'Token <b> {JWT} </b>'
    """
    try:
        new_user_type = user_type_repo.create(
            db=db, obj_in=UserType(name=user_type_in.name.upper(), id=uuid.uuid4())
        )
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message=f"{user_type_in.name.upper() } created successfully",
            data=UserType(id=new_user_type.id, name=new_user_type.name),
        )
    except IntegrityError:
        db.rollback()
        raise AlreadyExistsException(
            detail=error_strings.ALREADY_EXISTS.format(
                "user type with name " + user_type_in.name
            )
        )


@router.get(
    "/{user_type_id}/all_users",
    response_model=GenericResponse[List[UserInResponse]],
    dependencies=[Depends(admin_permission_dependency)],
)
def get_all_users_of_user_type(
    user_type_id: str,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
) ->GenericResponse[List[UserInResponse]]:
    """
    This endpoint gets all the users under a particular user type.
    Only superusers have access to this endpoint.
    """
    target_user_type = user_type_repo.get(db, id=user_type_id)
    if not target_user_type:
        raise ObjectNotFoundException()

    return create_response(
        message="Successful",
        status_code=status.HTTP_200_OK,
        data=[
            UserInResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                is_active=user.is_active,
                user_type=UserTypeInDB(id=user.user_type.id, name=user.user_type.name),
                verify_token="",
            )
            for user in target_user_type.users
        ],
    )
