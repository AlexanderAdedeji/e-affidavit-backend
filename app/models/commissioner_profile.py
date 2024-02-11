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
    court_id = Column(
        String, nullable=False
    )  # Assuming court ID is a string; adjust as necessary
    signature = Column(String, nullable=False)  # Path to signature image or similar
    stamp = Column(String, nullable=False)  # Path to stamp image or similar
    user_id = Column(String, ForeignKey("users.id"))
    created_by_id = Column(String, ForeignKey("users.id"))

    # Relationship to link back to the User model
    user = relationship("User", back_populates="commissioner_profile")
    courts = relationship("Court", back_populates="commissioner_profile")


# Update the User model to include a reverse relationship
