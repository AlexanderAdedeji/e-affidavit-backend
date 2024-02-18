# import jwt
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import Integer, Column, Boolean, String, ForeignKey
from sqlalchemy.orm import relationship
from commonLib.models.base_class import Base

from app.core.settings.configurations import settings


class HeadOfUnit(Base):
    __tablename__ = "head_of_unit"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    jurisdiction_id = Column(
        String,  ForeignKey("jurisdictions.id"), nullable=False
      
    )  # Assuming court ID is a string; adjust as necessary
    user_id = Column(String, ForeignKey("users.id"))
    created_by_id = Column(String, ForeignKey("users.id"))

    # Relationship to link back to the User model
    user = relationship("User", foreign_keys=[user_id], back_populates="head_of_unit")
    created_by = relationship("User", foreign_keys=[created_by_id])
    jurisdiction = relationship("Jurisdiction", back_populates="head_of_units")



# Update the User model to include a reverse relationship


