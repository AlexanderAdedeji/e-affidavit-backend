from pydantic import BaseModel
from typing import Any, Dict, Optional
from app.core.settings.configurations import settings


class Email(BaseModel):
    template_id: str
    template_dict: str
    recipient: str
    sender: str


class EmailCreate(Email):
    pass


class EmailUpdate(BaseModel):
    delivered: bool
    extra_data: Optional[str]


class EmailTemplateVariables(BaseModel):
    name: str


class ResetPasswordEmailTemplateVariables(EmailTemplateVariables):
    reset_link: str
    valid_for: Optional[int] = int(settings.RESET_TOKEN_EXPIRE_MINUTES) / 1000




class UserActivationTemplateVariables(EmailTemplateVariables):
    pass


class UserDeactivationTemplateVariables(EmailTemplateVariables):
    pass


class UserCreationTemplateVariables(EmailTemplateVariables):
    action_url:str
  

class UserVerificationTemplateVariables(UserCreationTemplateVariables):
    pass
class OperationsInviteTemplateVariables(BaseModel):
    invite_url:str
    name:str
    invite_sender_name:str
    invite_sender_organization_name:str
  
    user_role:str