from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, validator
from app.schemas.court_system_schema import CourtSystemInDB

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


class UserWithToken(UserBase):
    email: EmailStr
    user_type: UserTypeInDB
    token: str


class UserInResponse(UserBase):
    id: str
    is_active:bool
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
    email: EmailStr
    user_type_id: str
    court_id: Optional[str] = None
    jurisdiction_id: Optional[str] = None

class CreateInvite(InviteOperationsForm):
    id:str
    invited_by_id:str
    token:str

class AcceptedInviteResponse(BaseModel):
    first_name:str
    last_name:str
    email:EmailStr
    invite_id:str
    is_accepted:bool
    user_type:UserTypeInDB

class CommissionerProfileBase(UserBase):
    id: str
    email: EmailStr
    is_active:bool
    court: str
 
class CommissionerProfileCreate(BaseModel):
    court_id:str
    commissioner_id:str
    created_by_id:str


class HeadOfUnitBase(BaseModel):
    head_of_unit_id:str
    created_by_id:str
    jurisdiction_id:str

class CommissionerAttestation(BaseModel):
    signature: str
    stamp: str


class FullCommissionerInResponse(UserBase):
    email: EmailStr
    is_active: bool

    court: CourtSystemInDB


class FullCommissionerProfile(FullCommissionerInResponse):
    attestation: CommissionerAttestation
    user_type: UserTypeInDB
class FullHeadOfUniteInResponse(UserBase):
    email:EmailStr
    is_active:bool
    jurisdiction:CourtSystemInDB
    user_type:UserTypeInDB


