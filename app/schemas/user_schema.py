from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, validator
from app.schemas.court_system import CourtSystemInDB

from app.schemas.user_type_schema import UserTypeInDB


class UserBase(BaseModel):
    first_name: str
    last_name: str


class UserCreateForm(UserBase):
    email: EmailStr
    password: str


class UserCreate(UserCreateForm):
    user_type_id: str







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
    verify_token: Optional[str]


class UserVerify(BaseModel):
    token: str


class ResetPasswordSchema(BaseModel):
    token: str
    password: str

###Operations Create
class OperationsCreateForm(BaseModel):
    invite_id:str
    password:str

class CommissionerCreate(OperationsCreateForm):
    court_id: str

class HeadOfUnitCreate(OperationsCreateForm):
    jurisdiction_id: str


class InviteTokenData(BaseModel):
    invite_id: str


class InviteOperationsForm(BaseModel):
    first_name: str
    last_name: str
    email: str
    user_type_id: str
    court_id: Optional[str] = None
    jurisdiction_id: Optional[str] = None

class CreateInvite(InviteOperationsForm):
    id:str
    invited_by_id:str
    token:str



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
    court: CourtSystemInDB
    user_type: UserTypeInDB



