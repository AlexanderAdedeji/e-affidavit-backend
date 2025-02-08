
import pytest
from datetime import datetime
from pydantic import ValidationError
from app.schemas.payment_schema import (
    PaymentCreate,
    PaymentInDB,
    PaymentUpdate,
    PaymentStatus,
)




def test_payment_create_valid():
    """Test that valid data for PaymentCreate passes validation."""
    data = {
        "user_id": "user1234",
        "document_id": "doc5678",
        "reference": "ref_abcdefgh12345678"
    }
    payment_create = PaymentCreate(**data)
    assert payment_create.user_id == "user1234"
    assert payment_create.document_id == "doc5678"
    assert payment_create.reference == "ref_abcdefgh12345678"


def test_payment_create_missing_field():
    """Test that missing a required field (e.g. 'reference') raises a validation error."""
    data = {
        "user_id": "user1234",
        "document_id": "doc5678"
        # Missing 'reference'
    }
    with pytest.raises(ValidationError) as exc_info:
        PaymentCreate(**data)
    error_msg = str(exc_info.value)
    # Check that the error message mentions the missing "reference" field.
    assert "reference" in error_msg




def test_payment_in_db_valid():
    """Test that valid data for PaymentInDB passes validation."""
    data = {
        "id": "payment1234",
        "user_id": "user1234",
        "document_id": "doc5678",
        "amount": 1500.00,
        "status": "success",  
        "payment_method": "card",
        "paystack_reference": "ref_abcdefgh12345678",
        "created_at": datetime(2024, 11, 27, 14, 23, 45, 678000),
        "updated_at": datetime(2024, 11, 27, 15, 0, 1, 0)
    }
    payment_db = PaymentInDB(**data)
    assert payment_db.amount == 1500.00
    assert payment_db.status == PaymentStatus.success


def test_payment_in_db_negative_amount():
    """Test that a negative amount for PaymentInDB raises a validation error."""
    data = {
        "id": "payment1234",
        "user_id": "user1234",
        "document_id": "doc5678",
        "amount": -100.00,
        "status": "failed",
        "payment_method": "card",
        "paystack_reference": "ref_abcdefgh12345678",
        "created_at": datetime.now(),
        "updated_at": None
    }
    with pytest.raises(ValidationError) as exc_info:
        PaymentInDB(**data)
    error_msg = str(exc_info.value)
    assert "non-negative" in error_msg 



def test_payment_update_empty():
    """Test that creating a PaymentUpdate with no fields is allowed (all fields are optional)."""
    update = PaymentUpdate()
    assert update.status is None
    assert update.payment_method is None
    assert update.amount is None
    assert update.paystack_reference is None


def test_payment_update_valid():
    """Test that valid update data passes validation."""
    data = {
        "status": "success",
        "payment_method": "bank_transfer",
        "amount": 2000.00,
        "paystack_reference": "ref_xyz987654321"
    }
    update = PaymentUpdate(**data)

    assert update.status == PaymentStatus.success
    assert update.amount == 2000.00
    assert update.payment_method == "bank_transfer"
    assert update.paystack_reference == "ref_xyz987654321"


def test_payment_update_negative_amount():
    """Test that providing a negative amount in PaymentUpdate raises a validation error."""
    data = {
        "amount": -50.0
    }
    with pytest.raises(ValidationError) as exc_info:
        PaymentUpdate(**data)
    error_msg = str(exc_info.value)
    assert "non-negative" in error_msg
