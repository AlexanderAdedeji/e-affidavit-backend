from datetime import timedelta
from typing import List
from postmarker import core
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from app.core.settings.configurations import settings
from sqlalchemy.orm import Session
from app.api.dependencies.db import get_db
from app.core.errors import error_strings
from app.core.errors.exceptions import (
    AlreadyExistsException,
    DisallowedLoginException,
    DoesNotExistException,
    IncorrectLoginException,
)
from app.core.services.jwt import get_user_email_from_token
from app.repositories.user_repo import user_repo
from app.schemas.email_schema import UserCreationTemplateVariables

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
from app.core.services.email import email_service


router = APIRouter()


def check_unique_user(db: Session, user_in: UserCreate):
    user_with_same_email = user_repo.get_by_email(db, email=user_in.email)
    if user_with_same_email:
        raise AlreadyExistsException(
            entity_name="user with email {}".format(user_in.email)
        )


def check_if_user_exist(db: Session, user_in: UserCreate):
    user_exist = user_repo.get_by_email(db, email=user_in.email)
    if not user_exist:
        raise DoesNotExistException(entity_name="user not found")
    return user_exist


@router.post("/login", response_model=GenericResponse[UserWithToken])
def login(
    user_login: UserInLogin,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = check_if_user_exist(db, user_in=user_login)
    

    if user is None or not user.verify_password(user_login.password):
        raise IncorrectLoginException()
    if not user.is_active:
        raise DisallowedLoginException(detail=error_strings.INACTIVE_USER_ERROR)

    template_dict = UserCreationTemplateVariables(
        name=f"{user.first_name} {user.last_name}",
    ).dict()

    background_tasks.add_task(
        email_service.send_email_with_template,
        client=core.PostmarkClient(server_token=settings.POSTMARK_API_TOKEN),
        template_id=settings.VERIFY_EMAIL_TEMPLATE_ID,
        template_dict=template_dict,
        recipient=user.email,
    )

    token = user.generate_jwt()
    return create_response(
        data=UserWithToken(
            email=user.email,
            token=token,
            user_type=UserTypeInDB(id=user.user_type_id, name=user.user_type.name),
        ),
        message="Login successfully",
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.post("/verify", status_code=status.HTTP_200_OK, response_model=GenericResponse)
def verify_user(token: UserVerify, db: Session = Depends(get_db)):
    """
    Verify user route. Expects token sent in the email link.
    If the token is invalid or expired, raises an exception.
    """
    email = get_user_email_from_token(token.token)
    user = user_repo.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    user = user_repo.activate(db, db_obj=user)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong!",
        )
    token = user.generate_jwt()
    verification_link = ""

    return create_response(
        message="Verification Successful",
        status_code=status.HTTP_202_ACCEPTED,
        data=UserInResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            user_type=UserTypeInDB(id=user.user_type_id, name=user.user_type.name),
            verify_token=token,
        ),
    )


@router.post("/resend_verification_token", status_code=status.HTTP_200_OK)
def resend_token(
    email: str, background_task: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Resend Verification Token route. Expects email, where the verification link would be sent to.
    If the email does not exist, raises exception
    """
    user = user_repo.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email not found"
        )

    verify_jwt_token = user_repo.create_verification_token(db, email=user.email)
    # verification_link = f"{FRONTEND_BASE_URL}{VERIFY_EMAIL_LINK}={verify_jwt_token}"
    # template_dict = UserverifyTemplateVariables(
    #     name=f"{user.first_name} {user.last_name}", verify_url=verification_link
    # ).dict()
    # background_task.add_task(
    #     send_email_with_template,
    #     client=core.PostmarkClient(server_token=settings.POSTMARK_API_TOKEN),
    #     template_id=VERIFY_EMAIL_TEMPLATE_ID,
    #     template_dict=template_dict,
    #     recipient=user.email,
    # )

    return create_response(
        message="Verification link sent successfully",
        data=verify_jwt_token,
        status_code=status.HTTP_200_OK,
    )


@router.post("/forgot_password", status_code=status.HTTP_200_OK)
def forgot_password(
    email: str, background_task: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Forgot Password route. Expects email, where the reset password link would be sent to.
    If the email does not exist, raises exception.
    """
    user = user_repo.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email not found"
        )

    reset_jwt_token = user_repo.create_verification_token(db, email=user.email)
    # template_dict = ResetPasswordEmailTemplateVariables(
    #     name=f"{user.first_name} {user.last_name}",
    #     reset_link=f"{FRONTEND_BASE_URL}{RESET_PASSWORD_URL}={reset_jwt_token}",
    # ).dict()
    # background_task.add_task(
    #     send_email_with_template,
    #     client=core.PostmarkClient(server_token=settings.POSTMARK_API_TOKEN),
    #     # template_id=RESET_PASSWORD_TEMPLATE_ID,
    #     template_id=VERIFY_EMAIL_TEMPLATE_ID,
    #     template_dict=template_dict,
    #     recipient=user.email,
    # )

    return {
        "message": "Password reset link sent successfully",
        "token":reset_jwt_token
    }


@router.post("/reset_password", status_code=status.HTTP_200_OK)
def reset_password(
    reset_password_data: ResetPasswordSchema, db: Session = Depends(get_db)
):
    """
    Reset Password route. Expects a token and new password for resetting the user's password.
    If the token is invalid or email does not exist, raises an exception.
    """
    token = reset_password_data.token
    password = reset_password_data.password
    email = get_user_email_from_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    user = user_repo.get_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email not found"
        )

    user = user_repo.update_password(db, user, password)
    token = user.generate_jwt()

    return token
