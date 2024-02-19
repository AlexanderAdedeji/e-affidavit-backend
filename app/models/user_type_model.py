# import jwt
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from commonLib.models.base_class import Base

from app.core.settings.configurations import settings


class UserType(Base):
    __tablename__ = "user_types"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    users = relationship("User", back_populates="user_type")
    invite_user_type = relationship("UserInvite", back_populates="user_type")