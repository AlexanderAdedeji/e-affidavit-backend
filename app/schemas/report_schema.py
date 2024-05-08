from app.schemas.affidavit_schema import SlimDocumentInResponse
from typing import List
from app.schemas.user_schema import FullCommissionerInResponse
from pydantic import BaseModel


class DocumentReports(BaseModel):
    name: str
    attested_date: str
    date_created:str


class CommissionersReport(BaseModel):
    commissioner: FullCommissionerInResponse
    attested_documents: List[SlimDocumentInResponse]


class CommissionerReport(BaseModel):
    commissioner: FullCommissionerInResponse
    attested_documents: List[DocumentReports]
