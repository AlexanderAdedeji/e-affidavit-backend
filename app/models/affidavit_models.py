from typing import Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import Column, String,ForeignKey
from sqlalchemy.orm import relationship
from commonLib.models.base_class import Base

from app.core.settings.configurations import settings


from commonLib.models.mongo_base_class import MongoBase


class Templates(MongoBase):
    data: Dict[str, Any]


class Documents(MongoBase):
    data: Dict[str, Any]


# import jwt


class AffidavitCategory(Base):
    __tablename__ = "affidavit_categories"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    name = Column(String, unique=True, nullable=False)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="category_created_by")

    def __init__(self, name: str, created_by_id: str):
        self.name = name
        self.created_by_id = created_by_id
