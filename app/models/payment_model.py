from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String

from commonLib.models.base_class import Base


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    document_id = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(50), nullable=False)
    payment_method = Column(String(50), nullable=True)
    paystack_reference = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __init__(
        self,
        user_id: str,
        document_id: str,
        amount: float,
        status: str,
        paystack_reference: str,
        payment_method: str = None,
    ):
        self.user_id = user_id
        self.document_id = document_id
        self.amount = amount
        self.status = status
        self.paystack_reference = paystack_reference
        self.payment_method = payment_method
