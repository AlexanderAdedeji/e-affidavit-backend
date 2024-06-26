from pydantic import BaseModel


class AdminDashboardStat(BaseModel):
    total_users: int
    total_affidavits: int
    total_revenue: int
    total_templates: int


class PublicDashboardStat(BaseModel):
    total_saved: int
    total_paid: int
    total_attested: int
    total_documents: int


class HeadOfUnitDashboardStat(BaseModel):
    total_courts: int
    total_commissioners: int
    total_revenue: int
    total_affidavits: int