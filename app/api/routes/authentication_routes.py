import string
from datetime import timedelta
from typing import List, Optional

from app.api.routes.user_routes import VERIFY_EMAIL_LINK
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from postmarker import core
from sqlalchemy.orm import Session

from app.api.dependencies.authentication import get_currently_authenticated_user
from app.api.dependencies.db import get_db
from app.core.errors import error_strings
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DisallowedLoginException,
    DoesNotExistException,
    IncorrectLoginException,
    ServerException,
    UnauthorizedEndpointException,
)
from app.core.services.email import email_service
from app.core.services.jwt import jwt_service
from app.core.settings.configurations import settings
from app.core.settings.logs.handler import logger
from app.core.settings.security import security
from app.models.user_model import User
from app.repositories.commissioner_profile_repo import comm_profile_repo
from app.repositories.user_repo import user_repo
from app.schemas.authentication_schema import ChangePassword, UserUpdate
from app.schemas.email_schema import (
    ResetPasswordEmailTemplateVariables,
    UserCreationTemplateVariables,
    UserVerificationTemplateVariables,
)
from app.schemas.user_schema import (
    ResetPasswordSchema,
    UserCreate,
    UserInLogin,
    UserInResponse,
    UserVerify,
    UserWithToken,
)
from app.schemas.user_type_schema import UserTypeInDB
from commonLib.response.response_schema import GenericResponse, create_response

router = APIRouter()


def get_frontend_url(user_type_name: str) -> Optional[str]:
    """
    Retrieve the frontend URL based on the user type.
    """
    url_map = {
        settings.PUBLIC_USER_TYPE: settings.PUBLIC_FRONTEND_BASE_URL,
        settings.ADMIN_USER_TYPE: settings.ADMIN_FRONTEND_BASE_URL,
        settings.HEAD_OF_UNIT_USER_TYPE: settings.COURT_SYSTEM_FRONTEND_BASE_URL,
        settings.COMMISSIONER_USER_TYPE: settings.COURT_SYSTEM_FRONTEND_BASE_URL,
    }
    frontend_url = url_map.get(user_type_name)
    logger.debug(f"Frontend URL for user type '{user_type_name}': {frontend_url}")
    return frontend_url

def handle_verification_email(user:User, db: Session, background_task: BackgroundTasks) -> None:
    """
    Wrapper for resending the verification email.
    """
    try:
        front_end_url = get_frontend_url(user.user_type.name)
        logger.info(front_end_url)
        if not front_end_url:
            logger.error(f"Frontend URL not found for user type: {user.user_type.name}")
            raise ServerException(detail="Frontend URL configuration error")
        verify_jwt_token = user_repo.create_verification_token(db, email=user.email)
        verification_link = f"{front_end_url}{settings.VERIFY_EMAIL_LINK}{verify_jwt_token}"
        template_dict = UserVerificationTemplateVariables(
            name=f"{user.first_name} {user.last_name}", action_url=verification_link
        ).dict()
        logger.info(f"Verification link generated: {verification_link}")
        email_service.send_email_with_template(
            db=db,
            template_id=settings.VERIFY_EMAIL_TEMPLATE_ID,
            template_dict=template_dict,
            recipient=user.email,
            background_tasks=background_task,
        )
    except Exception as e:
        logger.error(f"Error handling verification email for {user.email}: {e}")
        raise HTTPException(status=500, detail="Something went wrong")


def validate_commissioner_device(user: User, user_login: UserInLogin, db: Session, background_task: BackgroundTasks) -> None:
    """
    Validates the commissioner's device during login.
    """
    if user.commissioner_profile.device_id:
        if not user_login.device_id:
            logger.warning("Device ID missing for commissioner login.")
            raise IncorrectLoginException("Device ID is required for commissioner login.")
        if user.commissioner_profile.device_id != user_login.device_id:
            logger.warning("Device ID mismatch for commissioner login.")
            raise DisallowedLoginException(
                "Login is restricted to your registered device. Please contact support to update your registered device."
            )
    else:
        logger.warning("Commissioner has no registered device; deactivating account.")
        user_repo.deactivate(db, db_obj=user)
        handle_verification_email(user, db, background_task)
        raise DisallowedLoginException(
            "Commissioner must have a registered device to login. Check mail to reactivate."
        )


@router.post("/login")
def login(
    user_login: UserInLogin,
    background_task: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Login endpoint that verifies the user credentials and returns a JWT token.
    """
 
    user = user_repo.get_by_email(db, email=user_login.email)
    if not user or not user.verify_password(user_login.password):
            logger.warning(f"Login failed for email: {user_login.email}")
            raise IncorrectLoginException()

    if not user.is_active:
            logger.info(f"User {user.email} is inactive. Resending verification email.")
            handle_verification_email(user=user, db=db, background_task=background_task)
 
            raise DisallowedLoginException(
            detail="Your account is not verified. Check your mail for a new verification email."
        )

        # if user.user_type.name == settings.COMMISSIONER_USER_TYPE:
        #     validate_commissioner_device(user, user_login, db, background_task)
    try:
        token = user.generate_jwt()
        logger.info(f"User {user.email} logged in successfully.")
        return create_response(
            data=UserWithToken(
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                token=token,
                user_type=UserTypeInDB(id=user.user_type_id, name=user.user_type.name),
            ),
            message="Login successfully",
            status_code=status.HTTP_202_ACCEPTED,
        )
    except Exception as e:
        logger.error(f"Error in login endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed due to internal error.")


@router.post("/verify_email/", status_code=status.HTTP_200_OK, response_model=GenericResponse)
def verify_user(
    token: UserVerify,
    device_id: Optional[str] = Body(None),
    db: Session = Depends(get_db),
):
    """
    Verifies the user using the token from the verification email.
    Optionally accepts a device_id for commissioners.
    """
    try:
        logger.info(f"Verifying email with token: {token.token} and device_id: {device_id}")
        email_extracted = jwt_service.get_user_email_from_token(token.token)
        user = user_repo.get_by_email(db, email=email_extracted)
        if not user:
            logger.warning(f"Verification failed: No user found for email {email_extracted}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

        user = user_repo.activate(db, db_obj=user)
        if user.user_type.name == settings.COMMISSIONER_USER_TYPE:
            if not user.commissioner_profile.device_id:
                if device_id:
                    comm_profile_repo.update_device_id(device_id=device_id, commissioner_id=user.id, db=db)
                    logger.info(f"Device ID updated for commissioner {user.email}")
                else:
                    logger.warning("Device ID is required for commissioner verification.")
                    raise DisallowedLoginException(detail="Device ID is required for this user type.")
        logger.info(f"Email verified successfully for user {user.email}")
        return create_response(
            message="Email Verification Successful",
            status_code=status.HTTP_202_ACCEPTED,
        )
    except HTTPException as http_exc:
        logger.error(f"HTTP error during verification: {http_exc.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in verify_email endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Verification failed due to internal error.")


@router.post("/resend_verification_token", status_code=status.HTTP_200_OK, response_model=GenericResponse[UserInResponse])
def resend_token(
    email: str, background_task: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Resend Verification Token endpoint.
    Sends a new verification link to the user's email.
    """
    try:
        logger.info(f"Resending verification token to {email}")
        user = user_repo.get_by_email(db, email=email)
        if not user:
            logger.warning(f"Resend token failed: Email {email} not found.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        handle_verification_email(user=user, db=db, background_task=background_task)
        return create_response(
            message="Verification link sent successfully",
            status_code=status.HTTP_200_OK,
            data=UserInResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                is_active=user.is_active,
                user_type=UserTypeInDB(name=user.user_type.name, id=user.user_type.id),
            ),
        )
    except Exception as e:
        logger.error(f"Error resending verification token: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not resend verification token")


@router.post("/forgot_password", status_code=status.HTTP_200_OK)
def forgot_password(
    email: str, background_task: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Forgot Password endpoint.
    Sends a password reset link to the user's email.
    """
    try:
        logger.info(f"Password reset requested for {email}")
        user = user_repo.get_by_email(db, email=email)
        if not user:
            logger.warning(f"Forgot password failed: Email {email} not found.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        front_end_url = get_frontend_url(user.user_type.name)
        reset_jwt_token = user_repo.create_reset_password_token(db, email=user.email)
        template_dict = ResetPasswordEmailTemplateVariables(
            name=f"{user.first_name} {user.last_name}",
            reset_link=f"{front_end_url}{settings.RESET_PASSWORD_URL}{reset_jwt_token}",
        ).dict()
        email_service.send_email_with_template(
            template_id=settings.RESET_PASSWORD_TEMPLATE_ID,
            db=db,
            background_tasks=background_task,
            template_dict=template_dict,
            recipient=user.email,
        )
        logger.info(f"Password reset link sent to {email}")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Password reset link sent successfully",
            data=reset_jwt_token,
        )
    except Exception as e:
        logger.error(f"Error in forgot_password endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error sending password reset link")


@router.post("/reset_password", status_code=status.HTTP_200_OK)
def reset_password(
    reset_password_data: ResetPasswordSchema, db: Session = Depends(get_db)
):
    """
    Reset Password endpoint.
    Resets the user password using the provided token and new password.
    """
    try:
        logger.info("Reset password requested.")
        token = reset_password_data.token
        password = reset_password_data.password
        email_extracted = jwt_service.get_user_email_from_token(token)
        if not email_extracted:
            logger.warning("Invalid or expired token during password reset.")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
        user = user_repo.get_by_email(db, email=email_extracted)
        if not user:
            logger.warning(f"Password reset failed: User with email {email_extracted} not found.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not found")
        user = user_repo.update_password(db, user, password)
        new_token = user.generate_jwt()
        logger.info(f"Password reset successfully for {user.email}")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Password changed successfully",
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in reset_password endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error resetting password")


@router.patch("/change_password", response_model=GenericResponse[GenericResponse])
def change_password(
    password_in: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Change Password endpoint.
    Allows an authenticated user to change their password.
    """
    try:
        logger.info(f"Change password request for user {current_user.email}")
        if not current_user.verify_password(password_in.old_password):
            logger.warning("Incorrect old password provided.")
            raise UnauthorizedEndpointException(detail="Incorrect Password")
        user_repo.update(
            db,
            db_obj=current_user,
            obj_in={
                "hashed_password": security.get_password_hash(password=password_in.new_password)
            },
        )
        logger.info(f"Password changed successfully for user {current_user.email}")
        return create_response(
            status_code=status.HTTP_200_OK,
            message="Password Changed successfully",
        )
    except Exception as e:
        logger.error(f"Error in change_password endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error changing password")


@router.patch("/update_user_profile")
def update_user(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_currently_authenticated_user),
):
    """
    Update User Profile endpoint.
    Allows a user to update their profile information.
    """
    try:
        logger.info(f"Updating profile for user {current_user.email}")
        updated_user = user_repo.update(db, db_obj=current_user, obj_in=user_in)
        logger.info(f"Profile updated successfully for user {current_user.email}")
        return create_response(
            message="Account Profile Updated Successfully",
            status_code=status.HTTP_200_OK,
            data=UserInResponse(
                id=updated_user.id,
                first_name=updated_user.first_name,
                last_name=updated_user.last_name,
                email=updated_user.email,
                is_active=updated_user.is_active,
                user_type=UserTypeInDB(
                    id=updated_user.user_type_id, name=updated_user.user_type.name
                ),
            ),
        )
    except Exception as e:
        logger.error(f"Error in update_user_profile endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating profile")
