from pydantic import BaseModel


class CourtSystemBase(BaseModel):
    name: str


class CreateCourt(CourtSystemBase):
    jurisdiction_id: int


class CreateJurisdiction(CourtSystemBase):
    state_id: int


class CreateState(CourtSystemBase):
    pass


class CourtSystemInDB(CourtSystemBase):
    id: int


class FullCourtInDB(CourtSystemBase):
    id:int
    state: str
    jurisdiction: str


