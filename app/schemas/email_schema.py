from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, HttpUrl, constr

from app.core.settings.configurations import settings


class Email(BaseModel):
    template_id: str
    template_dict: Dict[str, Any]
    recipient: EmailStr
    sender: EmailStr

    class Config:
        orm_mode = True


class EmailCreate(Email):
    pass


class EmailUpdate(BaseModel):
    delivered: bool
    extra_data: Optional[str] = None


class EmailTemplateVariables(BaseModel):
    name: constr(min_length=1, max_length=255)


class ResetPasswordEmailTemplateVariables(EmailTemplateVariables):
    reset_link: HttpUrl
    # Convert the RESET_TOKEN_EXPIRE_MINUTES to a number (here as an integer division)
    valid_for: Optional[int] = int(settings.RESET_TOKEN_EXPIRE_MINUTES) // 1000

    class Config:
        orm_mode = True


class UserActivationTemplateVariables(EmailTemplateVariables):
    pass


class UserDeactivationTemplateVariables(EmailTemplateVariables):
    pass


class UserCreationTemplateVariables(EmailTemplateVariables):
    action_url: HttpUrl


class UserVerificationTemplateVariables(UserCreationTemplateVariables):
    pass


class OperationsInviteTemplateVariables(BaseModel):
    invite_url: HttpUrl
    name: constr(min_length=1, max_length=255)
    invite_sender_name: constr(min_length=1, max_length=255)
    invite_sender_organization_name: constr(min_length=1, max_length=255)
    user_role: constr(min_length=1, max_length=100)
