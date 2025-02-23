from datetime import datetime
from typing import Annotated, Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas.affidavit_schema import SlimDocumentInResponse
from app.schemas.shared_schema import SlimUserInResponse


class CourtSystemBase(BaseModel):
    name: Annotated[str, Field(...,min_length=1, max_length=255)]

    @field_validator("name")
    def strip_and_validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be empty or whitespace")
        return value

    class Config:
        orm_mode = True


class CreateCourt(CourtSystemBase):
    jurisdiction_id: str  # Consider adding a UUID validation if needed


class CreateJurisdiction(CourtSystemBase):
    state_id: str  # Consider adding a UUID validation if needed


class CreateState(CourtSystemBase):
    pass


class CourtSystemInDB(CourtSystemBase):
    id: Any  # In production, you might narrow this to str or UUID


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
    head_of_unit: str 
    courts: int
    name: str

    @field_validator("name")
    def strip_and_validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name must not be empty")
        return value


class CourtBase(CourtSystemBase):
    id: str
    date_created: datetime
    jurisdiction: CourtSystemInDB


class CourtInResponse(CourtBase):
    commissioners: List[SlimUserInResponse]
    documents: List[SlimDocumentInResponse]
