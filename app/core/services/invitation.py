import uuid

from fastapi import BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from postmarker import core
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies.db import get_db
from app.core.services.email import email_service
from app.core.services.jwt import jwt_service
from app.core.settings.configurations import settings
from app.models.user_invite_models import UserInvite
from app.models.user_model import User
from app.repositories.user_invite_repo import user_invite_repo
from app.repositories.user_type_repo import user_type_repo
from app.schemas.user_schema import CreateInvite, InviteOperationsForm

# async def process_user_invite(
#     user: InviteOperationsForm,
#     current_user: User,
#     db: Session,
#     background_tasks: BackgroundTasks,
# ):
#     try:
#         invite_in = UserInvite(
#             first_name=user.first_name,
#             last_name=user.last_name,
#             user_type_id=user.user_type_id,
#             email=user.email,
#             court_id=user.court_id or None,
#             jurisdiction_id=user.jurisdiction_id or None,
#             invited_by_id=current_user.id,
#         )

#         db.add(invite_in)
#         db.commit()
#         db.refresh(invite_in)
#         logger.debug(invite_in.id)
#         token = jwt_service.generate_invitation_token(str(invite_in.id))

#         invite_in.token = token
#         db.commit()
#         db.refresh(invite_in)

#         organisation = determine_organisation(invite_in)
#         operations = determine_operations_base_url(invite_in.user_type.name)

#         send_invitation_email(
#             background_tasks,
#             invite_in,
#             organisation,
#             operations,
#             token,
#             db,
#             current_user,
#         )
#     except SQLAlchemyError as e:
#         logger.error(
#             f"Database error while processing invitation for {user.email}: {str(e)}"
#         )
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="A database error occurred. Please try again later.",
#         )
#     except Exception as e:
#         logger.error(f"Failed to process invitation for {user.email}: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Data integrity error: Please check the data you are passing.",
#         )


# def determine_organisation(user: InviteOperationsForm) -> str:
#     if user.court_id:
#         return user.court.name
#     elif user.jurisdiction_id:
#         return user.jurisdiction.name
#     return "E-AFFIDAVIT"


# def determine_operations_base_url(user_type: str) -> str:
#     return (
#         settings.ADMIN_FRONTEND_BASE_URL
#         if user_type == settings.ADMIN_USER_TYPE
#         else settings.COURT_SYSTEM_FRONTEND_BASE_URL
#     )


# def send_invitation_email(
#     background_tasks: BackgroundTasks,
#     invite: CreateInvite,
#     organisation: str,
#     operations: str,
#     token: str,
#     current_user: User,
#     db: Session,
# ):
#     template_dict = {
#         "name": f"{invite.first_name} {invite.last_name}",
#         "invite_sender_organization_name": organisation,
#         "invite_url": f"{operations}{settings.ACCEPT_INVITE_URL}{token}",
#         "user_role": invite.user_type.name.capitalize(),
#         "invite_sender_name": f"{current_user.first_name}",
#     }
#     print(template_dict["invite_url"])

#     email_service.send_email_with_template(
#         db=db,
#         template_id=settings.OPERATIONS_INVITE_TEMPLATE_ID,
#         background_tasks=background_tasks,
#         template_dict=template_dict,
#         recipient=invite.email,
#     )


async def process_user_invite(
    user: InviteOperationsForm,
    current_user: User,
    db: Session,
    background_tasks: BackgroundTasks,
):
    try:
        # Create a new UserInvite instance
        invite_in = UserInvite(
            first_name=user.first_name,
            last_name=user.last_name,
            user_type_id=user.user_type_id,
            email=user.email,
            court_id=user.court_id,
            jurisdiction_id=user.jurisdiction_id,
            invited_by_id=current_user.id,
        )

        # Add to database and commit
        db.add(invite_in)
        db.commit()
        db.refresh(invite_in)
        logger.debug(f"New invite created with ID: {invite_in.id}")

        # Generate token
        token = jwt_service.generate_invitation_token(str(invite_in.id))
        invite_in.token = token
        db.commit()
        db.refresh(invite_in)

        # Determine organization and operations base URL
        organisation = determine_organisation(invite_in)
        operations = determine_operations_base_url(invite_in.user_type.name)

        # Send invitation email
        send_invitation_email(
            background_tasks,
            invite_in,
            organisation,
            operations,
            token,
            current_user,
            db,
        )
        logger.info(f"Invitation email sent to {user.email}")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"Database error while processing invitation for {user.email}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Error processing invitation for {user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An error occurred while processing the invitation.",
        )


def determine_organisation(invite: UserInvite) -> str:
    if invite.court_id and invite.court:
        return invite.court.name
    if invite.jurisdiction_id and invite.jurisdiction:
        return invite.jurisdiction.name
    return "E-AFFIDAVIT"


def determine_operations_base_url(user_type: str) -> str:
    if user_type == settings.ADMIN_USER_TYPE:
        return settings.ADMIN_FRONTEND_BASE_URL
    return settings.COURT_SYSTEM_FRONTEND_BASE_URL


def send_invitation_email(
    background_tasks: BackgroundTasks,
    invite: UserInvite,
    organisation: str,
    operations: str,
    token: str,
    current_user: User,
    db: Session,
):
    template_dict = {
        "name": f"{invite.first_name} {invite.last_name}",
        "invite_sender_organization_name": organisation,
        "invite_url": f"{operations}{settings.ACCEPT_INVITE_URL}{token}",
        "user_role": invite.user_type.name.capitalize(),
        "invite_sender_name": current_user.first_name,
    }
    logger.debug(f"Email invite URL: {template_dict['invite_url']}")

    email_service.send_email_with_template(
        db=db,
        template_id=settings.OPERATIONS_INVITE_TEMPLATE_ID,
        background_tasks=background_tasks,
        template_dict=template_dict,
        recipient=invite.email,
    )
