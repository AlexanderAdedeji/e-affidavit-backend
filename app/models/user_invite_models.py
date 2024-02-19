from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from commonLib.models.base_class import (
    Base,
)  


class UserInvite(Base):
    __tablename__ = "user_invites"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    user_type_id = Column(String,ForeignKey("user_types.id"), nullable=False)
    token = Column(String, unique=True, nullable=False)
    court_id=Column(String, ForeignKey("courts.id"), nullable=True)
    jurisdiction_id=Column(String,ForeignKey("jurisdictions.id"), nullable=True)
    is_accepted = Column(Boolean, default=False, nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    invited_by_id = Column(String, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="invited_by")
    court = relationship("Court", back_populates="user_invite")
    jurisdiction= relationship("Jurisdiction", back_populates="user_invite")
    user_type = relationship("UserType", back_populates="invite_user_type")
    

    # def __repr__(self):
    #     return f"<UserInvite email={self.email} token={self.token} is_accepted={self.is_accepted}>"



