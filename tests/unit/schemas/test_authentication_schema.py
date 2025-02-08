# tests/unit/schemas/test_authentication_schema.py

import re
import pytest
from pydantic import ValidationError

from app.schemas.authentication_schema import ChangePassword, UserUpdate
from app.schemas.user_schema import InviteOperationsForm



def test_change_password_valid():
    """Test that valid data passes."""
    valid_data = {
        "old_password": "OldPass123",
        "new_password": "NewPass123"
    }
    cp = ChangePassword(**valid_data)
    assert cp.old_password == "OldPass123"
    assert cp.new_password == "NewPass123"

def test_change_password_new_password_missing_letter():
    """Test that a new password with digits only fails (missing letter)."""
    invalid_data = {
        "old_password": "OldPass123",
        "new_password": "12345678"
    }
    with pytest.raises(ValidationError) as exc_info:
        ChangePassword(**invalid_data)
    assert "New password must contain at least one letter and one digit" in str(exc_info.value)

def test_change_password_new_password_missing_digit():
    """Test that a new password with letters only fails (missing digit)."""
    invalid_data = {
        "old_password": "OldPass123",
        "new_password": "PasswordOnly"
    }
    with pytest.raises(ValidationError) as exc_info:
        ChangePassword(**invalid_data)
    assert "New password must contain at least one letter and one digit" in str(exc_info.value)

def test_change_password_old_password_too_short():
    """Test that an old password shorter than the minimum length fails."""
    invalid_data = {
        "old_password": "short",  # Less than 8 characters.
        "new_password": "NewPass123"
    }
    with pytest.raises(ValidationError) as exc_info:
        ChangePassword(**invalid_data)
    # In Pydantic V2, the message typically contains "String should have at least"
    assert "String should have at least" in str(exc_info.value)

# ---------------------------
# Tests for UserUpdate
# ---------------------------
# Note: Since the schema requires first_name and last_name (even if Optional),
# we include them in our test data.

def test_user_update_valid():
    """Test that valid user update data passes."""
    valid_data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "address": "123 Main Street",
        "phone": "+1234567890123",  # Valid per regex: optional '+' followed by a non-zero digit.
        "password": "ValidPass1"
    }
    update = UserUpdate(**valid_data)
    assert update.first_name == "Alice"
    assert update.last_name == "Smith"
    assert update.phone == "+1234567890123"
    assert update.password == "ValidPass1"

def test_user_update_invalid_first_name():
    """Test that a first_name containing nonalphabetic characters fails."""
    invalid_data = {
        "first_name": "Al1ce",  # Contains a digit.
        "last_name": "Smith",
        "phone": "+1234567890123",
    }
    with pytest.raises(ValidationError) as exc_info:
        UserUpdate(**invalid_data)
    assert "Name must contain only alphabetic characters" in str(exc_info.value)

def test_user_update_invalid_last_name():
    """Test that a last_name containing symbols fails."""
    invalid_data = {
        "first_name": "Alice",
        "last_name": "Sm!th",  # Contains an exclamation mark.
        "phone": "+1234567890123",
    }
    with pytest.raises(ValidationError) as exc_info:
        UserUpdate(**invalid_data)
    assert "Name must contain only alphabetic characters" in str(exc_info.value)



def test_user_update_invalid_phone():
    """Test that a phone number not matching the regex pattern fails validation."""
    data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "phone": "0123456789",  # Invalid: starts with '0'
        "password": "ValidPass1"
    }
    with pytest.raises(ValidationError) as exc_info:
        UserUpdate(**data)
    error_msg = str(exc_info.value)
    # In Pydantic v2 the error message mentions "should match pattern"
    assert "should match pattern" in error_msg


def test_user_update_with_valid_password():
    """Test that a valid password passes validation."""
    data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "password": "ValidPass1"
    }
    update = UserUpdate(**data)
    assert update.password == "ValidPass1"

def test_user_update_with_invalid_password_no_uppercase():
    """Test that a password with no uppercase letter fails."""
    data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "password": "lowercase1"
    }
    with pytest.raises(ValidationError) as exc_info:
        UserUpdate(**data)
    assert "Password must contain at least one uppercase letter" in str(exc_info.value)

def test_user_update_with_invalid_password_no_lowercase():
    """Test that a password with no lowercase letter fails."""
    data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "password": "UPPERCASE1"
    }
    with pytest.raises(ValidationError) as exc_info:
        UserUpdate(**data)
    assert "Password must contain at least one lowercase letter" in str(exc_info.value)

def test_user_update_with_invalid_password_no_digit():
    """Test that a password with no digit fails."""
    data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "password": "NoDigitsHere"
    }
    with pytest.raises(ValidationError) as exc_info:
        UserUpdate(**data)
    assert "Password must contain at least one digit" in str(exc_info.value)

def test_user_update_optional_password_none():
    """Test that if the password is omitted, it remains None."""
    data = {
        "first_name": "Alice",
        "last_name": "Smith"
    }
    update = UserUpdate(**data)
    assert update.password is None

# ---------------------------
# Tests for InviteOperationsForm
# ---------------------------

def test_invite_operations_form_invalid_first_name():
    """Test that a first name shorter than 3 characters fails."""
    data = {
        "first_name": "Al",  # Too short: min_length=3 required.
        "last_name": "Blue",
        "email": "alblue@example.com",
        "user_type_id": "ut005"
        # court_id and jurisdiction_id are optional.
    }
    with pytest.raises(ValidationError) as exc_info:
        InviteOperationsForm(**data)
    # In Pydantic V2, the error message typically contains "String should have at least"
    assert "String should have at least" in str(exc_info.value)
