# tests/unit/test_user_schema.py
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.user_schema import (AcceptedInviteResponse, AdminInResponse,
                                     AllUsers, CommissionerAttestation,
                                     CommissionerCreate,
                                     CommissionerInResponse,
                                     CommissionerProfileBase,
                                     CommissionerProfileCreate, CreateInvite,
                                     FullCommissionerInResponse,
                                     FullCommissionerProfile,
                                     FullHeadOfUniteInResponse, HeadOfUnitBase,
                                     HeadOfUnitCreate, HeadOfUnitInResponse,
                                     InviteOperationsForm, InviteResponse,
                                     InviteTokenData, OperationsCreateForm,
                                     PublicInResponse, ResetPasswordSchema,
                                     UserBase, UserCreate, UserCreateForm,
                                     UserInLogin, UserInResponse, UserUpdate,
                                     UserVerify, UserWithToken)
from app.schemas.user_type_schema import UserTypeInDB


# --- Tests for UserBase ---
def test_user_base_trim_names():
    # Test that extra whitespace is trimmed.
    user = UserBase(first_name="  John  ", last_name="  Doe  ")
    assert user.first_name == "John"
    assert user.last_name == "Doe"

def test_user_base_empty_after_trim():
    # Passing a name that is empty after trimming should fail.
    with pytest.raises(ValidationError) as excinfo:
        UserBase(first_name="    ", last_name="Doe")
    assert "cannot be empty" in str(excinfo.value)

# --- Tests for UserCreateForm ---
def test_user_create_form_valid():
    data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice@example.com",
        "password": "Password123"
    }
    form = UserCreateForm(**data)
    assert form.email == "alice@example.com"
    assert form.password == "Password123"

def test_user_create_form_password_no_uppercase():
    data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice@example.com",
        "password": "password123"  # No uppercase letter.
    }
    with pytest.raises(ValidationError) as excinfo:
        UserCreateForm(**data)
    assert "at least one uppercase" in str(excinfo.value)

def test_user_create_form_password_no_lowercase():
    data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice@example.com",
        "password": "PASSWORD123"  # No lowercase letter.
    }
    with pytest.raises(ValidationError) as excinfo:
        UserCreateForm(**data)
    assert "at least one lowercase" in str(excinfo.value)

def test_user_create_form_password_no_digit():
    data = {
        "first_name": "Alice",
        "last_name": "Smith",
        "email": "alice@example.com",
        "password": "Password"  # No digit.
    }
    with pytest.raises(ValidationError) as excinfo:
        UserCreateForm(**data)
    assert "at least one digit" in str(excinfo.value)

# --- Tests for UserUpdate ---
def test_user_update_no_password():
    # When no password is provided, the field should remain None.
    data = {
        "first_name": "Bob",
        "last_name": "Jones",
        "email": "bob@example.com"
    }
    update = UserUpdate(**data)
    assert update.password is None

def test_user_update_with_valid_password():
    data = {"password": "ValidPass1"}
    update = UserUpdate(**data)
    assert update.password == "ValidPass1"

def test_user_update_with_invalid_password():
    data = {"password": "short"}  # Too short and missing criteria.
    with pytest.raises(ValidationError) as excinfo:
        UserUpdate(**data)
    # You might see an error about the minimum length from constr(min_length=8)
    assert "ensure this value has at least" in str(excinfo.value) or "at least one uppercase" in str(excinfo.value)

# --- Tests for UserInLogin ---
def test_user_in_login():
    data = {
        "email": "login@example.com",
        "password": "SomePassword123",
        "device_id": "deviceXYZ"
    }
    login = UserInLogin(**data)
    assert login.email == "login@example.com"
    assert login.device_id == "deviceXYZ"

# --- Tests for UserWithToken ---
def test_user_with_token():
    data = {
        "first_name": "Carol",
        "last_name": "White",
        "email": "carol@example.com",
        "user_type": UserTypeInDB(id="ut001", name="admin"),
        "token": "sometoken"
    }
    user = UserWithToken(**data)
    assert user.token == "sometoken"
    assert user.user_type.name == "admin"

# --- Tests for UserInResponse & AllUsers ---
def test_user_in_response():
    data = {
        "id": "user123",
        "first_name": "Dave",
        "last_name": "Green",
        "email": "dave@example.com",
        "is_active": True,
        "user_type": UserTypeInDB(id="ut002", name="public"),
        "verify_token": "verify123"
    }
    response = UserInResponse(**data)
    assert response.id == "user123"
    assert response.verify_token == "verify123"

def test_all_users():
    now = datetime.utcnow()
    data = {
        "id": "user456",
        "first_name": "Eve",
        "last_name": "Black",
        "email": "eve@example.com",
        "is_active": True,
        "user_type": UserTypeInDB(id="ut003", name="commissioner"),
        "verify_token": None,
        "date_created": now
    }
    user = AllUsers(**data)
    assert user.date_created == now

# --- Tests for UserVerify & ResetPasswordSchema ---
def test_user_verify():
    data = {"token": "sometoken"}
    verify = UserVerify(**data)
    assert verify.token == "sometoken"

def test_reset_password_schema():
    data = {"token": "reset123", "password": "NewPass123"}
    reset = ResetPasswordSchema(**data)
    assert reset.password == "NewPass123"

# --- Tests for Operations & Invite Schemas ---
def test_operations_create_form():
    data = {"invite_id": "invite123", "password": "OpsPass123"}
    ops = OperationsCreateForm(**data)
    assert ops.invite_id == "invite123"

def test_commissioner_create():
    data = {"invite_id": "invite123", "password": "CommPass123", "court_id": "court456"}
    comm = CommissionerCreate(**data)
    assert comm.court_id == "court456"

def test_head_of_unit_create():
    data = {"invite_id": "invite789", "password": "HeadPass123", "jurisdiction_id": "juris101"}
    hou = HeadOfUnitCreate(**data)
    assert hou.jurisdiction_id == "juris101"

def test_invite_operations_form_valid():
    data = {
        "first_name": "Frank",
        "last_name": "Blue",
        "email": "frank@example.com",
        "user_type_id": "ut004"
    }
    invite = InviteOperationsForm(**data)
    assert invite.first_name == "Frank"

def test_invite_operations_form_invalid_first_name():
    data = {
        "first_name": "Al",  # too short: min_length=3
        "last_name": "Blue",
        "email": "alblue@example.com",
        "user_type_id": "ut005"
    }
    with pytest.raises(ValidationError) as excinfo:
        InviteOperationsForm(**data)
    assert "ensure this value has at least" in str(excinfo.value)

def test_create_invite():
    data = {
        "first_name": "Grace",
        "last_name": "Brown",
        "email": "grace@example.com",
        "user_type_id": "ut006",
        "invited_by_id": "user999"
    }
    invite = CreateInvite(**data)
    assert invite.invited_by_id == "user999"

def test_accepted_invite_response():
    data = {
        "first_name": "Henry",
        "last_name": "Yellow",
        "email": "henry@example.com",
        "invite_id": "invite555",
        "is_accepted": True,
        "user_type": {"id": "ut007", "name": "admin"}
    }
    accepted = AcceptedInviteResponse(**data)
    assert accepted.is_accepted is True

# --- Tests for CommissionerAttestation ---
def test_commissioner_attestation():
    data = {"signature": "sigdata", "stamp": "stampdata"}
    attestation = CommissionerAttestation(**data)
    assert attestation.signature == "sigdata"

# --- Tests for FullCommissionerInResponse and FullCommissionerProfile ---
def test_full_commissioner_in_response():
    data = {
        "id": "user_comm1",
        "first_name": "Ian",
        "last_name": "Red",
        "email": "ian@example.com",
        "is_active": True,
        "court": {"id": "court123", "name": "Main Court"},
        "attested_documents": []
    }
    full_comm = FullCommissionerInResponse(**data)
    assert full_comm.id == "user_comm1"

def test_full_commissioner_profile():
    data = {
        "id": "user_comm2",
        "first_name": "Jack",
        "last_name": "Green",
        "email": "jack@example.com",
        "is_active": True,
        "court": {"id": "court124", "name": "Secondary Court"},
        "attested_documents": [],
        "attestation": {"signature": "sigs", "stamp": "stamps"},
        "user_type": {"id": "ut008", "name": "commissioner"}
    }
    profile = FullCommissionerProfile(**data)
    assert profile.attestation.signature == "sigs"
    assert profile.user_type.name == "commissioner"

# --- Tests for FullHeadOfUniteInResponse ---
def test_full_head_of_unit_in_response():
    data = {
        "first_name": "Karen",
        "last_name": "Blue",
        "email": "karen@example.com",
        "is_active": True,
        "jurisdiction": {"id": "juris555", "name": "Jurisdiction 555"},
        "user_type": {"id": "ut009", "name": "head_of_unit"}
    }
    head = FullHeadOfUniteInResponse(**data)
    # Depending on whether the model uses dicts or attributes, adjust accordingly.
    # For this example, we'll assume attribute access:
    assert head.jurisdiction.name == "Jurisdiction 555"

# --- Tests for AdminInResponse ---
def test_admin_in_response():
    now = datetime.utcnow()
    data = {
        "id": "admin001",
        "first_name": "Liam",
        "last_name": "Gray",
        "email": "liam@example.com",
        "is_active": True,
        "user_type": {"id": "ut010", "name": "admin"},
        "verify_token": "vtoken",
        "date_created": now,
        "templates_created": [],
        "users_invited": []
    }
    admin = AdminInResponse(**data)
    assert admin.date_created == now

# --- Tests for HeadOfUnitInResponse ---
def test_head_of_unit_in_response():
    now = datetime.utcnow()
    data = {
        "id": "unit001",
        "first_name": "Mia",
        "last_name": "Purple",
        "email": "mia@example.com",
        "is_active": True,
        "user_type": {"id": "ut011", "name": "head_of_unit"},
        "verify_token": "vtoken2",
        "date_created": now,
        "jurisdiction": {"id": "juris101", "name": "Jurisdiction101"},
        "courts": [{"id": "court101", "name": "Court 101", "date_created": now, "commissioners": 0, "documents": 0}],
        "commissioners": []
    }
    unit = HeadOfUnitInResponse(**data)
    assert unit.jurisdiction.name == "Jurisdiction101"

# --- Tests for CommissionerInResponse ---
def test_commissioner_in_response():
    now = datetime.utcnow()
    data = {
        "id": "comm001",
        "first_name": "Noah",
        "last_name": "Orange",
        "email": "noah@example.com",
        "is_active": True,
        "user_type": {"id": "ut012", "name": "commissioner"},
        "verify_token": "vtoken3",
        "date_created": now,
        "court": {"id": "court202", "name": "Court 202"},
        "attested_documents": []
    }
    comm = CommissionerInResponse(**data)
    assert comm.court.name == "Court 202"

# --- Tests for PublicInResponse ---
def test_public_in_response():
    now = datetime.utcnow()
    data = {
        "id": "public001",
        "first_name": "Olivia",
        "last_name": "Pink",
        "email": "olivia@example.com",
        "is_active": True,
        "user_type": {"id": "ut013", "name": "public"},
        "verify_token": "",
        "date_created": now,
        "document_saved": [],
        "document_attested": [],
        "document_paid": [],
        "total_documents": [],
        "total_amount": 0
    }
    public = PublicInResponse(**data)
    assert public.total_amount == 0

# --- Tests for InviteResponse ---
def test_invite_response():
    data = {
        "id": "invite001",
        "first_name": "Peter",
        "last_name": "Brown",
        "email": "peter@example.com",
        "status": "PENDING",
        "user_type": {"id": "ut014", "name": "public"},
        "date_created": "2024-01-01T00:00:00Z",
        "date_accepted": None
    }
    invite = InviteResponse(**data)
    assert invite.status == "PENDING"

