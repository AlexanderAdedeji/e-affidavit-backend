from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies.authentication import (
    admin_permission_dependency, get_currently_authenticated_user
)
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import AlreadyExistsException, DoesNotExistException, ServerException
from app.models.user_type_model import UserType
from app.repositories.user_type_repo import user_type_repo
from app.schemas.user_schema import UserInResponse
from app.schemas.user_type_schema import UserTypeBase, UserTypeCreate, UserTypeInDB
from commonLib.response.response_schema import GenericResponse, create_response

# Use our centralized Loguru logger from our application
from app.core.settings.logs.handler import logger

router = APIRouter(
    dependencies=[Depends(admin_permission_dependency)],
)

# --- Helper functions for DRY and defensive coding ---
def fetch_user_type_or_raise(db: Session, user_type_id: str) -> UserType:
    user_type = user_type_repo.get(db, user_type_id)
    if not user_type:
        msg = f"User type with ID '{user_type_id}' not found."
        logger.bind(event="USER_TYPE_NOT_FOUND", user_type_id=user_type_id).warning(msg)
        raise DoesNotExistException(entity_name="User type")
    return user_type

def get_filtered_user_types(db: Session) -> List[UserTypeInDB]:
    try:
        user_types = user_type_repo.get_all(db)
        # Exclude "superuser" types directly in Python;
        # for larger data sets consider filtering in the query.
        filtered = [
            UserTypeInDB(id=ut.id, name=ut.name)
            for ut in user_types
            if ut.name.lower() != "superuser"
        ]
        return filtered
    except Exception as e:
        logger.bind(event="FILTER_USER_TYPES").error(f"Error filtering user types: {e}", exc_info=True)
        raise ServerException(detail="Error fetching user types")

# --- Routes ---
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
    logger.bind(event="GET_ALL_USER_TYPES").info("Fetching all user types")
    try:
        filtered_user_types = get_filtered_user_types(db)
        logger.bind(event="GET_ALL_USER_TYPES_SUCCESS", count=len(filtered_user_types)).info("Successfully fetched user types")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="User types fetched successfully",
            data=filtered_user_types,
        )
    except Exception as e:
        logger.bind(event="GET_ALL_USER_TYPES_ERROR").error(f"Error fetching user types: {e}", exc_info=True)
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
    logger.bind(event="GET_SINGLE_USER_TYPE", user_type_id=user_type_id).info("Fetching user type")
    user_type = user_type_repo.get(db, user_type_id)
    if not user_type:
        logger.bind(event="GET_SINGLE_USER_TYPE_NOT_FOUND", user_type_id=user_type_id).warning("User type not found")
        raise DoesNotExistException(entity_name="User type")
    logger.bind(event="GET_SINGLE_USER_TYPE_SUCCESS", user_type_id=user_type_id).info("User type found")
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
    logger.bind(event="CREATE_USER_TYPE", name=user_type_in.name).info("Creating user type")
    try:
        new_user_type = user_type_repo.create(
            db=db, obj_in=UserType(name=user_type_in.name.upper())
        )
        logger.bind(event="CREATE_USER_TYPE_SUCCESS", name=new_user_type.name).info("User type created")
        return create_response(
            status_code=status.HTTP_201_CREATED,
            message=f"{user_type_in.name.upper()} created successfully",
            data=UserTypeBase(name=new_user_type.name),
        )
    except IntegrityError as ie:
        logger.bind(event="CREATE_USER_TYPE_DUPLICATE", name=user_type_in.name).warning("User type already exists", exc_info=True)
        db.rollback()
        raise AlreadyExistsException(entity_name=f"user type '{user_type_in.name}'")
    except Exception as e:
        logger.bind(event="CREATE_USER_TYPE_ERROR", name=user_type_in.name).error(f"Unexpected error: {e}", exc_info=True)
        raise ServerException(detail="An unexpected error occurred while creating user type")

@router.put(
    "/{user_type_id}",
    response_model=GenericResponse[UserTypeInDB],
    status_code=status.HTTP_202_ACCEPTED,
)
async def edit_user_type(user_type_id: str, user_type_in: UserTypeCreate, db: Session = Depends(get_db)):
    """
    Edit an existing user type by ID.
    Admin only.
    """
    logger.bind(event="EDIT_USER_TYPE", user_type_id=user_type_id).info("Updating user type")
    user_type_exist = fetch_user_type_or_raise(db, user_type_id)
    if user_type_repo.get_by_name(db, name=user_type_in.name):
        msg = f"User type with name '{user_type_in.name}' already exists."
        logger.bind(event="EDIT_USER_TYPE_DUPLICATE", user_type_name=user_type_in.name).warning(msg)
        raise AlreadyExistsException(entity_name=f"user type '{user_type_in.name}'")
    user_type_in.name = user_type_in.name.upper()
    updated_user_type = user_type_repo.update(db=db, obj_in=user_type_in, db_obj=user_type_exist)
    logger.bind(event="EDIT_USER_TYPE_SUCCESS", user_type_id=user_type_id).info("User type updated")
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
    logger.bind(event="DELETE_USER_TYPE", user_type_id=user_type_id).info("Deleting user type")
    if not user_type_repo.exist(db, user_type_id):
        logger.bind(event="DELETE_USER_TYPE_NOT_FOUND", user_type_id=user_type_id).warning("User type not found")
        raise DoesNotExistException(entity_name="User type")
    try:
        user_type_repo.remove(db=db, id=user_type_id)
        logger.bind(event="DELETE_USER_TYPE_SUCCESS", user_type_id=user_type_id).info("User type deleted successfully")
        return create_response(
            status_code=status.HTTP_204_NO_CONTENT,
            message="User type deleted successfully.",
        )
    except Exception as e:
        logger.bind(event="DELETE_USER_TYPE_ERROR", user_type_id=user_type_id).error(f"Error deleting user type: {e}", exc_info=True)
        raise ServerException(detail="An error occurred while deleting the user type")

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
    logger.bind(event="GET_USERS_BY_USER_TYPE", user_type_id=user_type_id).info("Fetching users for user type")
    target_user_type = user_type_repo.get(db, id=user_type_id)
    if not target_user_type:
        logger.bind(event="GET_USERS_BY_USER_TYPE_NOT_FOUND", user_type_id=user_type_id).warning("User type not found")
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
    logger.bind(event="GET_USERS_BY_USER_TYPE_SUCCESS", user_type_id=user_type_id, count=len(user_data)).info("Fetched users successfully")
    return create_response(
        message="Users fetched successfully",
        status_code=status.HTTP_200_OK,
        data=user_data,
    )
