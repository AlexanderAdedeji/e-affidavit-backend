from pydantic import BaseModel, Field, constr, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class PaymentStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"

class PaymentCreate(BaseModel):
    user_id: constr(min_length=1) = Field(
        ..., title="User ID", description="The ID of the user making the payment"
    )
    document_id: constr(min_length=1) = Field(
        ..., title="Document ID", description="The ID of the document being paid for"
    )
    reference: constr(min_length=1) = Field(
        ..., title="Paystack Reference", description="The reference returned by Paystack after initiating payment"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user1234",
                "document_id": "doc5678",
                "reference": "ref_abcdefgh12345678"
            }
        }

class PaymentInDB(BaseModel):
    id: constr(min_length=1) = Field(
        ..., title="Payment ID", description="The ID of the payment in the system"
    )
    user_id: constr(min_length=1) = Field(
        ..., title="User ID", description="The ID of the user making the payment"
    )
    document_id: constr(min_length=1) = Field(
        ..., title="Document ID", description="The ID of the document being paid for"
    )
    amount: float = Field(
        ..., ge=0, title="Amount", description="The amount of the payment (non-negative)"
    )
    status: PaymentStatus = Field(
        ..., title="Payment Status", description="The current status of the payment"
    )
    payment_method: Optional[constr(min_length=1)] = Field(
        None, title="Payment Method", description="Payment channel or method used"
    )
    paystack_reference: constr(min_length=1) = Field(
        ..., title="Paystack Reference", description="The reference returned by Paystack"
    )
    created_at: datetime = Field(
        ..., title="Created At", description="The timestamp when the payment was created"
    )
    updated_at: Optional[datetime] = Field(
        None, title="Updated At", description="The timestamp when the payment was last updated"
    )

    @validator("amount")
    def validate_amount(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Amount must be non-negative")
        return v

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "payment1234",
                "user_id": "user1234",
                "document_id": "doc5678",
                "amount": 1500.00,
                "status": "success",
                "payment_method": "card",
                "paystack_reference": "ref_abcdefgh12345678",
                "created_at": "2024-11-27T14:23:45.678Z",
                "updated_at": "2024-11-27T15:00:01.000Z"
            }
        }

class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = Field(
        None, title="Payment Status", description="The updated status of the payment"
    )
    payment_method: Optional[constr(min_length=1)] = Field(
        None, title="Payment Method", description="The payment method used for the payment"
    )
    amount: Optional[float] = Field(
        None, ge=0, title="Amount", description="Amount involved in the payment (non-negative)"
    )
    paystack_reference: Optional[constr(min_length=1)] = Field(
        None, title="Paystack Reference", description="The reference returned by Paystack"
    )

    @validator("amount")
    def validate_update_amount(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Amount must be non-negative")
        return v

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "payment_method": "bank_transfer",
                "amount": 1500.00,
                "paystack_reference": "ref_abcdefgh12345678"
            }
        }
