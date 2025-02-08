from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, constr, field_validator

from app.schemas.affidavit_schema import (SlimDocumentInResponse,
                                          SlimTemplateInResponse,
                                          TemplateInResponse)
from app.schemas.court_system_schema import CourtSystemInDB
from app.schemas.user_type_schema import UserTypeInDB


# Base user details shared across many models.
class UserBase(BaseModel):
    first_name: constr(min_length=3, max_length=50)
    last_name: constr(min_length=3, max_length=50)

    @field_validator("first_name", "last_name", mode="before")
    def trim_names(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Name must be a string")
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Name cannot be empty or just whitespace")
        return trimmed

    class Config:
        orm_mode = True


# Models used for user creation and update.
class UserCreateForm(UserBase):
    email: EmailStr
    password: constr(min_length=8)

    @field_validator("password")
    def validate_password(cls, v: str) -> str:
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserCreate(UserCreateForm):
    user_type_id: str


class UserUpdate(UserBase):
    email: Optional[EmailStr] = None
    first_name: Optional[constr(min_length=3, max_length=50)] = None
    last_name: Optional[constr(min_length=3, max_length=50)] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[constr(min_length=8)] = None

    @field_validator("password")
    def validate_password_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# Model used when a user logs in.
class UserInLogin(BaseModel):
    email: EmailStr
    password: str
    device_id: Optional[str] = None


class UserWithToken(UserBase):
    email: EmailStr
    user_type: UserTypeInDB
    token: str


class UserInResponse(UserBase):
    id: str
    is_active: bool
    email: EmailStr
    user_type: UserTypeInDB
    verify_token: Optional[str] = None


class AllUsers(UserInResponse):
    date_created: datetime


class UserVerify(BaseModel):
    token: str


class ResetPasswordSchema(BaseModel):
    token: str
    password: str


class OperationsCreateForm(BaseModel):
    invite_id: str
    password: str


class CommissionerCreate(OperationsCreateForm):
    court_id: str


class HeadOfUnitCreate(OperationsCreateForm):
    jurisdiction_id: str


class InviteTokenData(BaseModel):
    invite_id: str


class InviteOperationsForm(BaseModel):
    first_name: constr(min_length=3, max_length=50)
    last_name: constr(min_length=3, max_length=50)
    email: EmailStr
    user_type_id: str
    court_id: Optional[str] = None
    jurisdiction_id: Optional[str] = None


class CreateInvite(InviteOperationsForm):
    invited_by_id: str


class AcceptedInviteResponse(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    invite_id: str
    is_accepted: bool
    user_type: UserTypeInDB


class CommissionerProfileBase(UserBase):
    id: str
    email: EmailStr
    is_active: bool
    court: str


class CommissionerProfileCreate(BaseModel):
    court_id: str
    commissioner_id: str
    created_by_id: str


class HeadOfUnitBase(BaseModel):
    head_of_unit_id: str
    created_by_id: str
    jurisdiction_id: str


class CommissionerAttestation(BaseModel):
    signature: str
    stamp: str


class FullCommissionerInResponse(UserBase):
    id: str
    email: EmailStr
    is_active: bool
    court: CourtSystemInDB
    attested_documents: Optional[List[SlimDocumentInResponse]] = None


class FullCommissionerProfile(FullCommissionerInResponse):
    attestation: CommissionerAttestation
    user_type: UserTypeInDB


class FullHeadOfUniteInResponse(UserBase):
    email: EmailStr
    is_active: bool
    jurisdiction: CourtSystemInDB
    user_type: UserTypeInDB


class AdminInResponse(UserInResponse):
    date_created: datetime
    templates_created: List[SlimTemplateInResponse]
    users_invited: List[UserInResponse]


class HeadOfUnitInResponse(UserInResponse):
    date_created: datetime
    jurisdiction: CourtSystemInDB
    courts: List[CourtSystemInDB]
    commissioners: List[UserInResponse]


class CommissionerInResponse(UserInResponse):
    date_created: datetime
    court: CourtSystemInDB
    attested_documents: List[SlimDocumentInResponse]


class PublicInResponse(UserInResponse):
    document_saved: List[SlimDocumentInResponse]
    document_attested: List[SlimDocumentInResponse]
    document_paid: List[SlimDocumentInResponse]
    total_documents: List[SlimDocumentInResponse]
    total_amount: int
    date_created: datetime


class InviteResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    status: str
    user_type: UserTypeInDB
    date_created: str
    date_accepted: Optional[str] = None

    class Config:
        orm_mode = True
