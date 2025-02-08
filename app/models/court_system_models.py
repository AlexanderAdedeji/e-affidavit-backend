from uuid import uuid4

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import relationship

from commonLib.models.base_class import Base


class State(Base):
    __tablename__ = "states"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    name = Column(String, unique=True, index=True, nullable=False)
    jurisdictions = relationship(
        "Jurisdiction", back_populates="state", cascade="all, delete-orphan"
    )

    def __init__(self, name: str):
        self.name = name

    def save(self, session):
        try:
            session.add(self)
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            raise e


class Jurisdiction(Base):
    __tablename__ = "jurisdictions"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    name = Column(String, index=True, nullable=False)
    state_id = Column(String, ForeignKey("states.id"), nullable=False)
    state = relationship("State", back_populates="jurisdictions")
    courts = relationship(
        "Court", back_populates="jurisdiction", cascade="all, delete-orphan"
    )
    head_of_unit = relationship(
        "HeadOfUnit", back_populates="jurisdiction", uselist=False
    )
    user_invites = relationship("UserInvite", back_populates="jurisdiction")

    def __init__(self, name: str, state_id: int):
        self.name = name
        self.state_id = state_id


class Court(Base):
    __tablename__ = "courts"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    name = Column(String, index=True, nullable=False)
    jurisdiction_id = Column(String, ForeignKey("jurisdictions.id"), nullable=False)
    jurisdiction = relationship("Jurisdiction", back_populates="courts")
    commissioner_profiles = relationship(
        "CommissionerProfile", back_populates="court", cascade="all, delete-orphan"
    )
    user_invites = relationship("UserInvite", back_populates="court")

    def __init__(self, name: str, jurisdiction_id: str):
        self.name = name
        self.jurisdiction_id = jurisdiction_id
