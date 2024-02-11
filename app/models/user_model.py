# import jwt
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import Integer, Column, Boolean, String, ForeignKey
from sqlalchemy.orm import relationship
from commonLib.models.base_class import Base

from app.core.settings.configurations import settings




# JWT_EXPIRE_MINUTES=settings.JWT_EXPIRE_MINUTES
# JWT_ALGORITHM= settings.JWT_ALGORITHM
# SECRET_KEY =settings.SECRET_KEY
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    password = Column(String, nullable=False)
    user_type_id = Column(String, ForeignKey('user_types.id'))
    user_type = relationship("UserType", back_populates="users")
    commissioner_profile = relationship("CommissionerProfile", back_populates="user", uselist=False)
    head_of_unit = relationship("HeadOfUnit", back_populates="user")
