from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.orm import Session
from app.api.dependencies.authentication import (
    get_currently_authenticated_user,
    head_of_unit_permission_dependency,
    admin_permission_dependency,
)
from app.api.dependencies.db import get_db
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DoesNotExistException,
    UnauthorizedEndpointException,
)
from app.repositories.user_repo import UserRepositories, user_repo
from app.repositories.user_type_repo import UserTypeRepositories, user_type_repo
from app.core.settings.configurations import settings
from app.schemas.user_schema import (
    CommissionerCreate,
    CommissionerProfileBase,
    InvitePersonel,
)
from app.repositories.commissioner_profile_repo import comm_profile_repo


router = APIRouter()


@router.post("/create_head_of_unit")
async def create_head_of_unit(
    unit_head_in: CommissionerCreate,
    db: Session = Depends(get_db),
):
    # Validate the invitation
    invite_data = user_repo.get_user_invite_info(
        db=db, invite_id=unit_head_in.invite_id
    )
    if not invite_data:
        raise HTTPException(
            status_code=401, detail="Invitation does not exist or is invalid."
        )

    # Ensure the invite is for a commissioner
    user_type = user_type_repo.get(db=db, id=invite_data["user_type_id"])
    if user_type.name != settings.HEAD_OF_UNIT_USER_TYPE:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this endpoint.",
        )

    # Check if the email is already used
    if user_repo.get_by_email(db=db, email=unit_head_in.email):
        raise HTTPException(
            status_code=409,
            detail=f"User with email {unit_head_in.email} already exists.",
        )

    # Create the commissioner
    commissioner_data = unit_head_in.dict(exclude_unset=True)
    commissioner_data.update({"id": str(uuid.uuid4()), "user_type_id": user_type.id})
    new_commissioner = user_repo.create(db=db, obj_in=commissioner_data)

    # Create Commissioner Profile
    if new_commissioner:
        commissioner_profile_data = CommissionerProfileBase(
            court_id=invite_data["court_id"],  # Assuming invite_data contains court_id
            created_by_id=invite_data[
                "invited_by"
            ],  # Assuming invite_data contains invited_by
            user_id=new_commissioner.id,
        )
        comm_profile_repo.create(db=db, obj_in=commissioner_profile_data.dict())

    return new_commissioner


@router.get("/head_of_unit", dependencies=[Depends(admin_permission_dependency)])
def get_unit_head(unit_head_id: str, db: Session = Depends(get_db)):
    commissioner = user_repo.get(db=db, id=unit_head_id)
    if (
        commissioner is None
        or commissioner.user_type_id != settings.COMMISSIONER_USER_TYPE
    ):
        raise HTTPException(status_code=404, detail="Commissioner not found.")
    return commissioner


@router.get("/head_of_units", dependencies=[Depends(admin_permission_dependency)])
def get_unit_heads(db: Session = Depends(get_db)):
    user_type = user_type_repo.get_by_name(db=db, name=settings.COMMISSIONER_USER_TYPE)
    if user_type is None:
        raise HTTPException(status_code=500)
    commissioners = user_repo.get_users_by_user_type(db, user_type_id=user_type.id)
    return commissioners


@router.get("/me", dependencies=[Depends(head_of_unit_permission_dependency)])
def retrieve_current_unit_head(
    db: Session = Depends(get_db), user=Depends(get_currently_authenticated_user)
):
    return user_repo.get(db, id=user.id)


@router.put("/create_attestation")
def create_attestation(db: Session = Depends(get_db)):
    return {"notice": "Attestations are now being automatically created."}
