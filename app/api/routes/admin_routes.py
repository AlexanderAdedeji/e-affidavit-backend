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


@router.post("/invite_personel")
def invite_personel(personel: List[InvitePersonel], db: Session = Depends(get_db)):
    user_already_exist = []
    for user in personel:
        if user_repo.get_by_email(db, email=user.email):
            user_already_exist.append(user.email)
            continue
        url_params = (
            f"firstname={user.first_name}&lastname={user.last_name}&role={user.role}"
        )
        if user.role.lower() != "admin":
            url_params += f"&court={user.court}"
        invite_url = f"https://your-react-app.com/invite?{url_params}"

        logger.info(
            f"Sending invite to {user.first_name} {user.last_name} as a {user.role}"
        )
        # send_invite_email(email=user.email, invite_url=invite_url)

    if user_already_exist:
        raise HTTPException(
            status_code=409,
            detail=f"Emails already registered: {', '.join(user_already_exist)}",
        )

    return {"msg": "Invitations sent successfully"}


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





