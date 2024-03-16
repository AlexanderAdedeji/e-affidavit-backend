from pydantic import BaseModel


class AdminDashboardStat(BaseModel):
    total_users: int
    total_affidavits: int
    total_revenue: int
    total_commissioners: int
