from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from commonLib.models.base_class import (
    Base,
)  # Ensure you import your actual Base class from your database setup


class UserInvite(Base):
    __tablename__ = "user_invites"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False)
    is_accepted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    invited_by_id = Column(String, ForeignKey("users.id"), nullable=False)

    user = relationship("User", back_populates="invited_by_id")

    def __repr__(self):
        return f"<UserInvite email={self.email} token={self.token} is_accepted={self.is_accepted}>"
