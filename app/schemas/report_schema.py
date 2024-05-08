import datetime
from app.schemas.affidavit_schema import SlimDocumentInResponse
from typing import List
from app.schemas.user_schema import FullCommissionerInResponse
from pydantic import BaseModel


class DocumentReports(BaseModel):
    name: str
    attested_date: datetime.datetime
    date_created:datetime.datetime


class CommissionersReport(BaseModel):
    commissioner: FullCommissionerInResponse
    attested_documents: List[SlimDocumentInResponse]


class CommissionerReport(BaseModel):
    commissioner: FullCommissionerInResponse
    attested_documents: List[DocumentReports]
