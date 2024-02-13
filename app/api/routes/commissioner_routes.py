from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
)
from app.repositories.user_repo import user_repo
from app.repositories.user_type_repo import user_type_repo

from app.schemas.user_schema import CommissionerCreate, InvitePersonel


router = APIRouter()



@router.get("/create_commissioner")
def create_commissioner(
    commissioner_in: CommissionerCreate, db: Session = Depends(get_db)
):
    commissioner_exists = user_repo.get_by_email(db, email=commissioner_in.email)
    if commissioner_exists:
        raise AlreadyExistsException(
            detail=f"User with email {commissioner_in.email} already exists."
        )
    commissioner_in = commissioner_in.dict()
    user_type = user_type_repo.get(db, id=commissioner_in.role)
    if not user_type:
        raise DoesNotExistException(detail=f"usertype does not exist")
    commissioner_in.dict({"id": uuid.uuid4(), "user_type_id": commissioner_in.role})
    new_commissioner = user_repo.create(db, obj_in=commissioner_in)





