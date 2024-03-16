import uuid
from fastapi import BackgroundTasks, HTTPException, status
from loguru import logger
from app.core.services.email import email_service
from postmarker import core
from app.core.services.jwt import generate_invitation_token
from app.models.user_model import User
from app.repositories.user_invite_repo import user_invite_repo
from app.schemas.user_schema import CreateInvite, InviteOperationsForm
from sqlalchemy.orm import Session

from app.core.settings.configurations import settings


async def process_user_invite(
    user: InviteOperationsForm,
    current_user: User,
    db: Session,
    background_tasks: BackgroundTasks,
):
    invite_id = str(uuid.uuid4())
    token = generate_invitation_token(invite_id)

    invite_in = CreateInvite(
        id=invite_id,
        first_name=user.first_name,
        last_name=user.last_name,
        user_type_id=user.user_type_id,
        email=user.email,
        court_id=user.court_id or None,
        jurisdiction_id=user.jurisdiction_id or None,
        invited_by_id=current_user.id,
        token=token,
    )

    try:
        new_invite = user_invite_repo.create(db, obj_in=invite_in)
        organisation = determine_organisation(new_invite)
        operations = determine_operations_base_url(new_invite.user_type_id)

        send_invitation_email(
            background_tasks, new_invite, organisation, operations, token,db
        )
    except Exception as e:
        logger.error(f"Failed to process invitation for {user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data integrity Error: Please check the data you are passing.",
        )


def determine_organisation(user: InviteOperationsForm) -> str:
    if user.court_id:
        return user.court.name
    elif user.jurisdiction_id:
        return user.jurisdiction.name
    return "E-AFFIDAVIT"


def determine_operations_base_url(user_type_id: str) -> str:
    return (
        settings.ADMIN_FRONTEND_BASE_URL
        if user_type_id == settings.ADMIN_USER_TYPE
        else settings.COURT_SYSTEM_FRONTEND_BASE_URL
    )


def send_invitation_email(
    background_tasks: BackgroundTasks,
    invite: CreateInvite,
    organisation: str,
    operations: str,
    token: str,
    db:Session
):
    template_dict = {
        "name": f"{invite.first_name} {invite.last_name}",
        "organisation": organisation,
        "invite_url": f"{operations}/invite={token}",
        "user_role": invite.user_type.name.capitalize(),  # Ensure 'user_type.name' is correct
    }

    email_service.send_email_with_template(
        db=db,
        template_id=settings.OPERATIONS_INVITE_TEMPLATE_ID,
        background_tasks=background_tasks,
        template_dict=template_dict,
        recipient=invite.email,
    )
