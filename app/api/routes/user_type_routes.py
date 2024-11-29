from typing import List
from app.models.user_type_model import UserType
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
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
from commonLib.response.response_schema import GenericResponse, create_response
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter(
    dependencies=[Depends(admin_permission_dependency)],
)


@router.get(
    "/",
    response_model=GenericResponse[List[UserTypeInDB]],
    status_code=status.HTTP_200_OK,
)
async def get_all_user_types(db: Session = Depends(get_db)):
    """
    Retrieve a list of all user types in the application.
    Admin only.
    """
    logger.info("Fetching all user types")
    try:
        user_types = user_type_repo.get_all(db)
        filtered_user_types = [
            UserTypeInDB(id=user_type.id, name=user_type.name)
            for user_type in user_types
            if user_type.name.lower() != "superuser"
        ]
        return create_response(
            status_code=status.HTTP_200_OK,
            message="User types fetched successfully",
            data=filtered_user_types,
        )
    except Exception as e:
        logger.error(f"Error fetching user types: {e}")
        raise ServerException()


@router.get(
    "/{user_type_id}",
    response_model=GenericResponse[UserTypeBase],
    status_code=status.HTTP_200_OK,
)
async def get_single_user_type(user_type_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a single user type by ID.
    Admin only.
    """
    logger.info(f"Fetching user type with ID: {user_type_id}")
    user_type = user_type_repo.get(db, user_type_id)
    if not user_type:
        logger.warning(f"User type with ID {user_type_id} not found.")
        raise DoesNotExistException(entity_name="User type")

    return create_response(
        status_code=status.HTTP_200_OK,
        message="User type found",
        data=UserTypeBase(name=user_type.name),
    )


@router.post(
    "/",
    response_model=GenericResponse[UserTypeBase],
    status_code=status.HTTP_201_CREATED,
)
async def create_user_type(user_type_in: UserTypeCreate, db: Session = Depends(get_db)):
    """
    Create a new user type in the application.
    Admin only.
    """
    logger.info(f"Creating user type: {user_type_in.name}")
    try:
        new_user_type = user_type_repo.create(
            db=db, obj_in=UserType(name=user_type_in.name.upper())
        )
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message=f"{user_type_in.name.upper()} created successfully",
            data=UserTypeBase(name=new_user_type.name),
        )
    except IntegrityError:
        logger.warning(f"User type with name '{user_type_in.name}' already exists.")
        db.rollback()
        raise AlreadyExistsException(entity_name=f"user type '{user_type_in.name}'")


@router.put(
    "/{user_type_id}",
    response_model=GenericResponse[UserTypeInDB],
    status_code=status.HTTP_202_ACCEPTED,
)
async def edit_user_type(
    user_type_id: str, user_type_in: UserTypeCreate, db: Session = Depends(get_db)
):
    """
    Edit an existing user type by ID.
    Admin only.
    """
    logger.info(f"Updating user type with ID: {user_type_id}")
    user_type_exist = user_type_repo.get(db=db, id=user_type_id)

    if not user_type_exist:
        logger.warning(f"User type with ID {user_type_id} not found.")
        raise DoesNotExistException(entity_name="User type")

    exists = bool(user_type_repo.get_by_name(db, name=user_type_in.name))
    if exists:
        logger.warning(f"User type with name '{user_type_in.name}' already exists.")
        raise AlreadyExistsException(entity_name=f"user type '{user_type_in.name}'")

    user_type_in.name = user_type_in.name.upper()
    updated_user_type = user_type_repo.update(
        db=db, obj_in=user_type_in, db_obj=user_type_exist
    )

    return create_response(
        status_code=status.HTTP_202_ACCEPTED,
        message="User type updated successfully",
        data=UserTypeInDB(id=updated_user_type.id, name=updated_user_type.name),
    )


@router.delete("/{user_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_type(user_type_id: str, db: Session = Depends(get_db)):
    """
    Delete a user type by ID.
    Admin only.
    """
    logger.info(f"Deleting user type with ID: {user_type_id}")
    if not user_type_repo.exist(db, user_type_id):
        logger.warning(f"User type with ID {user_type_id} not found.")
        raise DoesNotExistException(entity_name="User type")

    user_type_repo.remove(db=db, id=user_type_id)
    logger.info(f"User type with ID {user_type_id} deleted successfully.")
    return create_response(
        status_code=status.HTTP_204_NO_CONTENT,
        message="User type deleted successfully.",
    )


@router.get(
    "/{user_type_id}/all_users",
    response_model=GenericResponse[List[UserInResponse]],
    status_code=status.HTTP_200_OK,
)
async def get_all_users_of_user_type(
    user_type_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Get all users associated with a particular user type.
    Admin only.
    """
    logger.info(f"Fetching users for user type ID: {user_type_id}")
    target_user_type = user_type_repo.get(db, id=user_type_id)
    if not target_user_type:
        logger.warning(f"User type with ID {user_type_id} not found.")
        raise DoesNotExistException(entity_name="User type")

    user_data = [
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
    ]

    return create_response(
        message="Users fetched successfully",
        status_code=status.HTTP_200_OK,
        data=user_data,
    )
