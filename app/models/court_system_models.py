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
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    state_id = Column(Integer, ForeignKey('states.id'))
    state = relationship("State", back_populates="jurisdictions")
    courts = relationship("Court", back_populates="jurisdiction")
    head_of_unit = relationship("HeadOfUnit", back_populates="head_of_unit")

class Court(Base):
    __tablename__ = "courts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    jurisdiction_id = Column(Integer, ForeignKey('jurisdictions.id'))
    jurisdiction = relationship("Jurisdiction", back_populates="courts")
    commissioner_profile = relationship("CommissionerProfile", back_populates = "courts")
