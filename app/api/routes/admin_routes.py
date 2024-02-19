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
from app.core.services.jwt import generate_invitation_token, get_all_details_from_token
from app.models.user_invite_models import UserInvite
from app.models.user_model import User
from app.core.settings.configurations import settings
from app.repositories.user_invite_repo import user_invite_repo
from app.repositories.user_repo import user_repo
from app.repositories.user_type_repo import user_type_repo
from app.api.dependencies.authentication import admin_permission_dependency
from app.schemas.user_schema import  CreateInvite, InviteOperationsForm,  UserCreate
from app.api.dependencies.authentication import get_currently_authenticated_user
from app.core.services.email import email_service


router = APIRouter()


# @router.post("/invite_personel", dependencies=[Depends(admin_permission_dependency)])
# def invite_personel(personel: List[InvitePersonel], db: Session = Depends(get_db)):
#     user_already_exist = []
#     for user in personel:
#         if user_repo.get_by_email(db, email=user.email):
#             user_already_exist.append(user.email)
#             continue
#         url_params = (
#             f"firstname={user.first_name}&lastname={user.last_name}&role={user.role}"
#         )
#         if user.role.lower() != "admin":
#             url_params += f"&court={user.court}"
#         invite_url = f"https://your-react-app.com/invite?{url_params}"

#         logger.info(
#             f"Sending invite to {user.first_name} {user.last_name} as a {user.role}"
#         )
#         # send_invite_email(email=user.email, invite_url=invite_url)

#     if user_already_exist:
#         raise HTTPException(
#             status_code=409,
#             detail=f"Emails already registered: {', '.join(user_already_exist)}",
#         )

#     return {"msg": "Invitations sent successfully"}


@router.post("/invite_personel")
async def invite_users(
    users: List[InviteOperationsForm],
    current_user: User = Depends(get_currently_authenticated_user),
    db: Session = Depends(get_db),
):
    tokens=[]
    for user in users:
        invite_id = str(uuid.uuid4())
        token = generate_invitation_token(id=invite_id)
        tokens.append({"email":user.email, "token":token })
        invite_in = CreateInvite(
            id=invite_id,
            first_name=user.first_name,
            last_name=user.last_name,
            user_type_id=user.user_type_id,
            email=user.email,
            court_id=user.court_id,
            jurisdiction_id=user.jurisdiction_id,
            invited_by_id=current_user.id,
            token=token
            
        )

        # try:
        new_invite =user_invite_repo.create(db, obj_in= invite_in)
        return new_invite
        # except Exception as e:
        #     logger.error(e)
    
        # Store token and user info in database
        # Assume db_session to be a dependency that provides a session to interact with your DB

        # Save the invitation in your DB with user details and the generated token
        # Send invitation email
        # email_service.send_email_with_template(user.email, token)
    return tokens


@router.get("/accept-invite/{token}")
async def accept_invite(token: str, db: Session = Depends(get_db)):
    # Step 1: Validate the JWT token and extract invite_id
    try:
        invite_info = get_all_details_from_token(token)
        invite_id = invite_info.get("inv_id")
    except Exception as e:  # Consider catching more specific exceptions
        raise HTTPException(status_code=400, detail=f"Token validation error: {str(e)}")

    # Step 2: Retrieve and validate the invite
    invite: UserInvite = user_repo.get_invite_by_id(db, invite_id=invite_id)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found or invalid.")
    if invite.is_accepted:
        raise HTTPException(
            status_code=400, detail="This invitation has already been accepted."
        )

    # Optionally, here you could update the invite to mark it as accepted to prevent reuse
    # user_repo.mark_invite_as_accepted(db, invite_id=invite_id)

    # Return a response or redirect the user to account creation page
    # Since FastAPI is backend, consider how you handle this in your frontend application
    return {
        "message": "Invite validated, proceed to account creation.",
        "invite_details": invite_info,
    }


@router.get("/admins")
def get_all_admins(db: Session = Depends(get_db)):
    """Get all admin users"""
    user_type = user_type_repo.get_by_name(db, name=settings.ADMIN_USER_TYPE)
    admins = user_repo.get_users_by_user_type(db, user_type.id)
    return admins


@router.get("/get_admin/{id}")
def get_admin(id:str, db:Session = Depends(get_db)) :
    """Get an admin by ID"""
    admin = user_repo.get(db, id=id)
    return admin

@router.get("/me", dependencies=[Depends(admin_permission_dependency)])
def retrieve_current_admin(
    db: Session = Depends(get_db), user=Depends(get_currently_authenticated_user)
):
    return user_repo.get(db, id=user.id)
    
