# from uuid import uuid4
# from sqlalchemy.sql.sqltypes import JSON
# from commonLib.models.base_class import Base
# from sqlalchemy import Column, ForeignKey, Integer, Boolean, String


# class Email(Base):
#     __tablename__ = "email" 
#     id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
#     delivered = Column(Boolean, default=False, nullable=False)
#     recipient = Column(String, nullable=False)
#     template_id = Column(String, nullable=False)
#     template_dict = Column(JSON, nullable=False)
#     sender = Column(String, nullable=False)
#     extra_data = Column(String, default="")

from sqlalchemy.sql.sqltypes import JSON
from commonLib.models.base_class import Base
from sqlalchemy import Column, String, Boolean
from uuid import uuid4

class Email(Base):
    __tablename__ = "emails" 
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    delivered = Column(Boolean, default=False, nullable=False)
    recipient = Column(String, nullable=False)
    template_id = Column(String, nullable=False)
    template_dict = Column(JSON, nullable=False)
    sender = Column(String, nullable=False)
    extra_data = Column(String, default="")

    def __init__(self, recipient: str, template_id: str, template_dict: dict, sender: str, extra_data: str = ""):
        self.recipient = recipient
        self.template_id = template_id
        self.template_dict = template_dict
        self.sender = sender
        self.extra_data = extra_data