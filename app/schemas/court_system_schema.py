from typing import Any, List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.schemas.affidavit_schema import SlimDocumentInResponse
from app.schemas.shared_schema import SlimUserInResponse, UsersWithSharedType


class CourtSystemBase(BaseModel):
    name: str


class CreateCourt(CourtSystemBase):
    jurisdiction_id: str


class CreateJurisdiction(CourtSystemBase):
    state_id: int


class CreateState(CourtSystemBase):
    pass


class CourtSystemInDB(CourtSystemBase):
    id: Any


class FullCourtInDB(CourtSystemBase):
    id: str
    state: str
    jurisdiction: str


class SlimCourtInResponse(CourtSystemInDB):
    date_created: datetime
    commissioners: int
    documents: int


class JurisdictionBase(CourtSystemBase):
    id: str
    date_created: datetime
    state: CourtSystemInDB
    head_of_unit: Optional[SlimUserInResponse] = None
    courts: List[SlimCourtInResponse]


class JurisdictionInResponse(JurisdictionBase):
    commissioners: List[SlimUserInResponse]
    documents: int


class SlimJurisdictionInResponse(BaseModel):
    id: str
    date_created: datetime
    courts: int
    name: str


class CourtBase(CourtSystemBase):
    id: str
    date_created: datetime
    jurisdiction: CourtSystemInDB


class CourtInResponse(CourtBase):
    commissioners: List[SlimUserInResponse]
    documents: List[SlimDocumentInResponse]
