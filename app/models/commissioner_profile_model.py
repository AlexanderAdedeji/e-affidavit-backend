# import jwt
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import Integer, Column, Boolean, String, ForeignKey
from sqlalchemy.orm import relationship
from commonLib.models.base_class import Base

from app.core.settings.configurations import settings


class CommissionerProfile(Base):
    __tablename__ = "commissioner_profiles"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    court_id = Column(String, ForeignKey("courts.id"), nullable=False)  # Adjust as necessary
    signature = Column(String, nullable=False)  # Path to signature image
    stamp = Column(String, nullable=False)  # Path to stamp image
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    created_by_id = Column(String, ForeignKey("users.id"))

    # Specify the foreign_keys for clarity

 

    user = relationship(
        "User", foreign_keys=[user_id], back_populates="commissioner_profile"
    )
    created_by = relationship("User", foreign_keys=[created_by_id])
    court = relationship("Court", back_populates="commissioner_profile")


# Update the User model to include a reverse relationship
