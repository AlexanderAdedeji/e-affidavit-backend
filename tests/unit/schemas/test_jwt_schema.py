from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.jwt_schema import JWTEMAIL, JWTInvite, JWTMeta, JWTUser


def test_jwt_user_valid():
    """Test that a valid JWTUser instance is created correctly."""
    user = JWTUser(id="user123")
    assert user.id == "user123"

def test_jwt_email_valid():
    """Test that a valid JWTEMAIL instance accepts a proper email."""
    email_instance = JWTEMAIL(email="test@example.com")
    assert email_instance.email == "test@example.com"

def test_jwt_email_invalid():
    """Test that providing an invalid email raises a ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        JWTEMAIL(email="not-an-email")
    assert "value is not a valid email address" in str(exc_info.value)

def test_jwt_invite_valid():
    """Test that a JWTInvite (which is a subclass of JWTUser) works correctly."""
    invite = JWTInvite(id="invite1")
    assert invite.id == "invite1"

def test_jwt_meta_valid():
    """Test that a valid JWTMeta instance is created correctly."""
    now = datetime.utcnow()
    exp_time = now + timedelta(hours=1)
    meta = JWTMeta(exp=exp_time, sub="mysubject")
    assert meta.exp == exp_time
    assert meta.sub == "mysubject"

def test_jwt_meta_invalid_exp():
    """Test that an invalid expiration value causes validation to fail."""
    with pytest.raises(ValidationError) as exc_info:
        JWTMeta(exp="not-a-datetime", sub="mysubject")
    assert "value is not a valid datetime" in str(exc_info.value)

def test_jwt_meta_exp_with_past_value():
    """
    Test that even if an expiration in the past is provided,
    the current validator (which is commented out) allows it.
    (If you later enable the check, adjust this test accordingly.)
    """
    past_time = datetime.utcnow() - timedelta(hours=1)
    meta = JWTMeta(exp=past_time, sub="expired")
    assert meta.exp == past_time

