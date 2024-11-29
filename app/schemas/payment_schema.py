from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime



class PaymentCreate(BaseModel):
    user_id: str = Field(..., title="User ID", description="The ID of the user making the payment")
    document_id: str = Field(..., title="Document ID", description="The ID of the document being paid for")
    reference: str = Field(..., title="Paystack Reference", description="The reference returned by Paystack after initiating payment")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user1234",
                "document_id": "doc5678",
                "reference": "ref_abcdefgh12345678"
            }
        }



class PaymentInDB(BaseModel):
    id: str = Field(..., title="Payment ID", description="The ID of the payment in the system")
    user_id: str = Field(..., title="User ID", description="The ID of the user making the payment")
    document_id: str = Field(..., title="Document ID", description="The ID of the document being paid for")
    amount: float = Field(..., title="Amount", description="The amount of the payment")
    status: str = Field(..., title="Payment Status", description="The current status of the payment")
    payment_method: Optional[str] = Field(None, title="Payment Method", description="Payment channel or method used")
    paystack_reference: str = Field(..., title="Paystack Reference", description="The reference returned by Paystack")
    created_at: datetime = Field(..., title="Created At", description="The timestamp when the payment was created")
    updated_at: Optional[datetime] = Field(None, title="Updated At", description="The timestamp when the payment was last updated")

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


# Schema for updating payment information (typically from webhook)
class PaymentUpdate(BaseModel):
    status: str = Field(..., title="Payment Status", description="The updated status of the payment")
    payment_method: Optional[str] = Field(None, title="Payment Method", description="The payment method used for the payment")
    amount: Optional[float] = Field(None, title="Amount", description="Amount involved in the payment")
    paystack_reference: Optional[str] = Field(None, title="Paystack Reference", description="The reference returned by Paystack")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "payment_method": "bank_transfer",
                "amount": 1500.00,
                "paystack_reference": "ref_abcdefgh12345678"
            }
        }
