"""This module provides a test-suite for end-to-end operations"""
import pytest
import requests

from datetime import datetime, timezone
from uuid import uuid4

from app.models.calculation import Calculation

# --------------------------------------------------------------
# E2E Fixtures
# --------------------------------------------------------------
@pytest.fixture
def base_url(fastapi_server: str) -> str:
    """Provides the base server URL"""
    return fastapi_server.rstrip("/")

@pytest.fixture
def registered_test_user(base_url: str, db_session):
    url = f"{base_url}/auth/register"
    user_data = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.doe@example.com",
        "username": "janedoe",
        "password": "SecurePass123",
        "confirm_password": "SecurePass123"
    }
    response = requests.post(url, json=user_data)
    assert response.status_code == 201, \
        "registered_test_user fixture failed to register"
    try:
        yield response.json()
    finally:
        pass


# --------------------------------------------------------------
# Health and Auth Endpoint Tests
# --------------------------------------------------------------
def test_health_endpoint(base_url: str):
    url = f"{base_url}/health"
    response = requests.get(url)
    assert response.status_code == 200, f"Unexpected status code {response.status_code}"
    assert response.json() == {"status": "ok"}, "Nonstandard response data from /health"

def test_user_registration(registered_test_user):
    data = registered_test_user
    for key in [
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_verified"]:
        assert key in data, f"'{key}' missing from registration response"
    assert data["username"] == "janedoe"
    assert data["email"] == "jane.doe@example.com"
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"
    assert data["is_active"] == True
    assert data["is_verified"] == False

def test_user_login(base_url: str, registered_test_user):
    login_url = f"{base_url}/auth/login"

    payload = {
        "username": registered_test_user["username"],
        "password": "SecurePass123"
    }
    response = requests.post(login_url, json=payload)
    assert response.status_code == 200, f"Login failure: {response.text}"

    data = response.json()
    required_fields = {
        "access_token": str,
        "refresh_token": str,
        "token_type": str,
        "expires_at": str,
        "user": dict,
    }
    for field, expected_type in required_fields.items():
        assert field in data, f"'{field}' field missing from login response"
        assert isinstance(data[field], expected_type), (
            f"Expected type {expected_type} in field {field}, "
            f"got {type(data[field])}"
        )
    assert data["token_type"].lower() == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    
    ttl = data["expires_at"]
    if ttl.endswith("Z"):
        ttl = ttl.replace("Z", "+00:00")
    expires_at = datetime.fromisoformat(ttl)
    current_time = datetime.now(timezone.utc)
    assert expires_at.tzinfo, "ttl datetime not timezone aware"
    assert expires_at > current_time

    user_data = data["user"]
    user_required_fields = {
        "username": str,
        "email": str,
        "first_name": str,
        "last_name": str,
        "is_active": bool,
        "is_verified": bool
    }
    for field, expected_type in user_required_fields.items():
        assert field in user_data, f"'{field}' field missing from user data"
        assert isinstance(user_data[field], expected_type), (
            f"Expected type {expected_type} in field {field}, "
            f"got {type(user_data[field])}"
        )
    assert user_data["username"] == registered_test_user["username"]
    assert user_data["email"] == registered_test_user["email"]
    assert user_data["first_name"] == registered_test_user["first_name"]
    assert user_data["last_name"] == registered_test_user["last_name"]
    assert user_data["is_active"]

