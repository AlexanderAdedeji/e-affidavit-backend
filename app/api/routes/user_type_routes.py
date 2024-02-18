from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.exc import IntegrityError
from starlette import status
from sqlalchemy.orm import Session
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    ServerException,
)
from app.repositories.user_type_repo import user_type_repo

from app.api.dependencies.authentication import admin_permission_dependency
from app.schemas.user_type_schema import UserTypeBase
from app.models.user_type_model import UserType
from commonLib.response.response_schema import GenericResponse, create_response


router = APIRouter()


@router.get(
    "/user_types",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[List[UserTypeBase]],
    # dependencies=[Depends(admin_permission_dependency)],
)
def get_all_user_types(db: Session = Depends(get_db)):
    user_types = user_type_repo.get_all(db)
    response = dict(
        data=[
            UserType(id=user_type.id, name=user_type.name) for user_type in user_types
        ],
        message="Onboarding successful",
        status=status.HTTP_200_OK,
    )
    return response


@router.get(
    "/user_type/{id}",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponse[UserTypeBase],
    dependencies=[Depends(admin_permission_dependency)],
)
async def get_single_user_type(*, id: str, db: Session = Depends(get_db)):
    user_type = user_type_repo.get(db, id)
    return create_reponse(
        status_code=status.HTTP_200_OK,
        message="usertype found",
        data=UserType(id=user_type.id, name=user_type.name),
    )


@router.delete(
    "/user_type/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(admin_permission_dependency)],
)
async def delete_user_type(*, id: str, db: Session = Depends(get_db)):
    if not user_type_repo.exist(db, id):
        raise DoesNotExistException(detail="No such usertype exists.")
    else:
        user_type_repo.remove(db=db, id=id)
        return create_reponse(
            status_code=status.HTTP_204_NO_CONTENT,
            message="User type deleted successfully.",
        )


@router.put(
    "/user_type/{id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenericResponse[UserTypeBase],
    dependencies=[Depends(admin_permission_dependency)],
)
async def edit_user_type(*, id: str, user_type: str, db: Session = Depends(get_db)):
    logger.info(type(id))
    try:
        user_type_exist = user_type_repo.get(db=db, id=id)

        if not user_type_exist:
            raise DoesNotExistException(detail="No such usertype exists.")

        else:
            updated_user_type = user_type_repo.update(
                db=db, obj_in=user_type, db_obj=user_type_exist
            )

        return create_reponse(
            status_code=status.HTTP_204_NO_CONTENT,
            message="User type edited successfully.",
            data=UserType(id=updated_user_type.id, name=updated_user_type.name),
        )
    except Exception as e:

        logger.error("Error in update operation", e)
        raise ServerException()


@router.post(
    "user_type",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponse[UserTypeBase],
    # dependencies=[Depends(admin_permission_dependency)],
)
def create_user_type(
    user_type: str,
    db: Session = Depends(get_db),
):
    """Create a new user type."""
    try:
        new_user = user_type_repo.create(
            db=db, obj_in=UserType(name=user_type.upper(), id=uuid.uuid4())
        )
        return create_reponse(
            status=status.HTTP_201_CREATED,
            message=f"{user_type.upper() } created successfully",
            data=UserType(id=new_user.id, name=new_user.name),
        )
    except IntegrityError:
        db.rollback()
        raise AlreadyExistsException(
            detail=f"A User Type with the name {user_type} already exist."
        )
