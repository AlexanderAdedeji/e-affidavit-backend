from typing import Any, List
from pydantic import BaseModel
from datetime import datetime

from app.schemas.user_schema import SlimUserInResponse, UserInResponse, UsersWithSharedType


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


class Jurisdiction(CourtSystemBase):
    id: str
    date_created: datetime
    state: CourtSystemInDB
    head_of_units: UsersWithSharedType
    courts: List[CourtSystemInDB]


class Court(CourtSystemBase):
    id: str
    date_created: datetime
    state: CourtSystemInDB
    Jurisdiction:CourtSystemInDB
    head_of_unit: SlimUserInResponse
    commissioners: List[UsersWithSharedType]

