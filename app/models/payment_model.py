import jwt
from datetime import datetime, timedelta
from uuid import uuid4
from loguru import logger
from sqlalchemy import Integer, Column, Boolean, String, ForeignKey,Numeric
from sqlalchemy.orm import relationship
from commonLib.models.base_class import Base
from app.schemas.jwt_schema import JWTEMAIL, JWTUser
from app.core.settings.configurations import settings
from app.core.settings.security import security


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(String, primary_key=True)
    # user_id = Column(String, ForeignKey('users.id'), nullable=False)
    document_id = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False) 
    # currency = Column(String(3), nullable=False)
    status = Column(String(50), nullable=False)
    payment_method = Column(String(50))
    paystack_reference = Column(String(50), unique=True, nullable=False)
    # user = relationship("User", back_populates="payments")









