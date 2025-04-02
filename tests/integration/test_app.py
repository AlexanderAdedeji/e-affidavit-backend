import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_root_redirect():
    """
    Test that the root endpoint ("/") redirects to the API documentation.
    """
    response = client.get("/")
    assert response.status_code in (302, 307)
    assert "/docs" in response.headers.get("location", "")

def test_health_endpoint():
    """
    If you have a health check endpoint (e.g., "/health"),
    you can test that it returns a 200 status and expected message.
    """
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data and data["status"] == "ok"

def test_create_user():
    """
    Test creating a new user via the API.
    This test assumes that your application has a POST /users endpoint that
    creates a new user and returns the created user data.
    """
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "password": "ValidPass123",
        "user_type_id": "ut001"
    }

    # Send a POST request to create the user.
    response = client.post("/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data["data"]
    assert data["data"]["email"] == "john.doe@example.com"

def test_create_user_invalid_email():
    """
    Test creating a new user via the API with an invalid email.
    """
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "invalid_email",
        "password": "ValidPass123",
        "user_type_id": "ut001"
    }

    # Send a POST request to create the user.
    response = client.post("/users", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data

def test_create_user_missing_fields():
    """
    Test creating a new user via the API with missing fields.
    """
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "user_type_id": "ut001"
    }

    # Send a POST request to create the user.
    response = client.post("/users", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


client = TestClient(app)

def test_root_redirect():
    """
    Test that the root endpoint ("/") redirects to the API documentation.
    """
    response = client.get("/")
    assert response.status_code in (302, 307)
    assert "/docs" in response.headers.get("location", "")

def test_health_endpoint():
    """
    If you have a health check endpoint (e.g., "/health"),
    you can test that it returns a 200 status and expected message.
    """
    response = client.get("/health")  
    assert response.status_code == 200
    data = response.json()
    assert "status" in data and data["status"] == "ok"

def test_create_user():
    """
    Test creating a new user via the API.
    This test assumes that your application has a POST /users endpoint that
    creates a new user and returns the created user data.
    """
 
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "password": "ValidPass123",  
        "user_type_id": "ut001"
    }

    # Send a POST request to create the user.
    response = client.post("/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data["data"]
    assert data["data"]["email"] == "john.doe@example.com"




