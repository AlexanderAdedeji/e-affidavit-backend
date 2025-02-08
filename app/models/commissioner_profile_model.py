# import jwt
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.settings.configurations import settings
from commonLib.models.base_class import Base


class CommissionerProfile(Base):
    __tablename__ = "commissioner_profiles"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    court_id = Column(String, ForeignKey("courts.id"), nullable=False)
    signature = Column(String, nullable=True)
    stamp = Column(String, nullable=True)
    commissioner_id = Column(String, ForeignKey("users.id"), unique=True)
    created_by_id = Column(String, ForeignKey("users.id"))
    device_id = Column(String, nullable=True)
    user = relationship(
        "User", foreign_keys=[commissioner_id], back_populates="commissioner_profile"
    )
    created_by = relationship("User", foreign_keys=[created_by_id])
    court = relationship("Court", back_populates="commissioner_profiles")
