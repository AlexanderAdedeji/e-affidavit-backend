# # import jwt
# from datetime import datetime, timedelta
# from uuid import uuid4
# from sqlalchemy import Integer, Column, Boolean, String, ForeignKey
# from sqlalchemy.orm import relationship
# from commonLib.models.base_class import Base

# from app.core.settings.configurations import settings


# class HeadOfUnit(Base):
#     __tablename__ = "head_of_units"
#     id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
#     jurisdiction_id = Column(String, ForeignKey("jurisdictions.id"), nullable=False)
#     head_of_unit_id = Column(String, ForeignKey("users.id"), nullable=False)
#     created_by_id = Column(String, ForeignKey("users.id"), nullable=False)

#     user = relationship(
#         "User",
#         foreign_keys=head_of_unit_id,
#         back_populates="head_of_unit",
#         uselist=False,
#     )
#     created_by = relationship("User", foreign_keys=[created_by_id])
#     jurisdiction = relationship("Jurisdiction", back_populates="head_of_unit")
from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from commonLib.models.base_class import Base


class HeadOfUnit(Base):
    __tablename__ = "head_of_units"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    jurisdiction_id = Column(String, ForeignKey("jurisdictions.id"), nullable=False)
    head_of_unit_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=False)

    user = relationship(
        "User",
        foreign_keys=head_of_unit_id,
        back_populates="head_of_unit",
        uselist=False,
    )
    created_by = relationship("User", foreign_keys=[created_by_id])
    jurisdiction = relationship("Jurisdiction", back_populates="head_of_unit")

    def __init__(self, jurisdiction_id: str, head_of_unit_id: str, created_by_id: str):
        self.jurisdiction_id = jurisdiction_id
        self.head_of_unit_id = head_of_unit_id
        self.created_by_id = created_by_id
