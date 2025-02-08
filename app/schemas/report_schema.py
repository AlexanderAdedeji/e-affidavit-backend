from datetime import datetime
from typing import List
from pydantic import BaseModel
from app.schemas.affidavit_schema import SlimDocumentInResponse
from app.schemas.user_schema import FullCommissionerInResponse


class DocumentReports(BaseModel):
    """
    A report model representing detailed document information for reporting purposes.
    """
    name: str
    attested_date: datetime
    date_created: datetime

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "name": "Affidavit Document 1",
                "attested_date": "2024-11-28T12:34:56Z",
                "date_created": "2024-11-27T14:23:45Z"
            }
        }


class CommissionersReport(BaseModel):
    """
    A report model aggregating a commissioner and a list of their attested documents.
    Attested documents are represented in a slim format.
    """
    commissioner: FullCommissionerInResponse
    attested_documents: List[SlimDocumentInResponse]

    class Config:
        orm_mode = True


class CommissionerReport(BaseModel):
    """
    A detailed report model for a commissioner that uses a more detailed document report.
    """
    commissioner: FullCommissionerInResponse
    attested_documents: List[DocumentReports]

    class Config:
        orm_mode = True
