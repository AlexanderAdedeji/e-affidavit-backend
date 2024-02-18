from typing import List, Optional

from pydantic import BaseModel, EmailStr, validator

from app.schemas.user_type_schema import UserTypeInDB


class UserBase(BaseModel):
    first_name: str
    last_name: str


class UserCreateForm(UserBase):
    email: EmailStr
    password: str


class UserCreate(UserCreateForm):
    user_type_id: str

    # @validator("phone")
    # def validate_phone(cls, value: str) -> str:
    #     return phone_validators.validate_phone_number(value)


class CommissionerCreate(UserCreate):
    invite_id: str
    court_id: str


class HeadOfUnitCreate(UserCreate):
    jurisdiction: str


class UserUpdate(UserBase):
    email: Optional[EmailStr]
    first_name: Optional[str]
    last_name: Optional[str]
    address: Optional[str]
    phone: Optional[str]
    password: Optional[str] = None


class UserInLogin(BaseModel):
    email: EmailStr
    password: str


class UserWithToken(BaseModel):
    email: EmailStr
    user_type: UserTypeInDB
    token: str


class UserInResponse(UserBase):
    id: str
    first_name: str
    last_name: str
    email: EmailStr
    user_type: UserTypeInDB
    verify_token: str


class UserVerify(BaseModel):
    token: str


class SlimUserInResponse(BaseModel):
    id: int
    email: EmailStr
    user_type: UserTypeInDB


class ResetPasswordSchema(BaseModel):
    token: str
    password: str


class InvitePersonel(BaseModel):
    first_name: str
    last_name: str
    email: str
    court: Optional[int]
    state: Optional[int]


class InviteTokenData(BaseModel):
    invite_id: str


class UserInvitation(InvitePersonel):
    pass


class CommissionerProfileBase(BaseModel):
    commissioner_id: str
    court_id: str
    created_by_id: str


class CommissionerAttestation(BaseModel):
    signature: str
    stamp: str


class FullCommissionerInResponse(UserBase):
    email: EmailStr
    is_active: bool
    attestation: CommissionerAttestation
    court: str
    user_type: UserTypeInDB
