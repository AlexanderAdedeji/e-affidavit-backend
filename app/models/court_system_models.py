from uuid import uuid4
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from commonLib.models.base_class import Base

class State(Base):
    __tablename__ = "states"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    jurisdictions = relationship("Jurisdiction", back_populates="state")

class Jurisdiction(Base):
    __tablename__ = "jurisdictions"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    name = Column(String, index=True, nullable=False)
    state_id = Column(Integer, ForeignKey('states.id'), nullable=False)
    state = relationship("State", back_populates="jurisdictions")
    courts = relationship("Court", back_populates="jurisdiction", cascade="all, delete")
    head_of_unit = relationship("HeadOfUnit", back_populates="jurisdiction", uselist=False)
    user_invites = relationship("UserInvite", back_populates="jurisdiction")

    

class Court(Base):
    __tablename__ = "courts"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    name = Column(String, index=True, nullable=False)
    jurisdiction_id = Column(String, ForeignKey('jurisdictions.id'), nullable=False)
    jurisdiction = relationship("Jurisdiction", back_populates="courts")
    commissioner_profiles = relationship("CommissionerProfile", back_populates="court", cascade="all, delete")
    user_invites = relationship("UserInvite", back_populates="court")











