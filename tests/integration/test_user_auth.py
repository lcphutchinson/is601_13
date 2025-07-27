"""This module provides a test suite for user authentication functions in the user module"""
import pytest
from uuid import UUID
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from tests.conftest import generate_user_data

def test_password_hashing(db_session, test_user):
    """Test password hashing and verification"""
    original_password = "TestPass123"
    hashed = User.hash_password(original_password)

    user = User(
        first_name=test_user.first_name,
        last_name=test_user.last_name,
        email=test_user.email,
        username=test_user.username,
        password=hashed
    )

    assert user.verify_password(original_password)
    assert user.verify_password("WrongPass123") is False
    assert hashed != original_password

def test_user_authentication(db_session):
    """Test user authentication and token generation"""
    user_data = generate_user_data()
    user_data['password'] = "TestPass123"
    user_data['confirm_password'] = "TestPass123"
    user = User.register(db_session, user_data)
    db_session.commit()

    auth_result = User.authenticate(
        db_session,
        user_data['username'],
        "TestPass123"
    )

    assert auth_result is not None
    assert "access_token" in auth_result
    assert "token_type" in auth_result
    assert auth_result["token_type"] == "bearer"
    assert "user" in auth_result

def test_email_authentication(db_session):
    """Test user authentication using email"""
    user_data = generate_user_data()
    user_data['password'] = "TestPass123"
    user_data['confirm_password'] = "TestPass123"
    user = User.register(db_session, user_data)
    db_session.commit()

    auth_result = User.authenticate(
        db_session,
        user_data['email'],
        "TestPass123"
    )

    assert auth_result is not None
    assert "access_token" in auth_result

def test_user_last_login_update(db_session):
    """Test that last_login is updated on authentication"""
    user_data = generate_user_data()
    user_data['password'] = "TestPass123"
    user_data['confirm_password'] = "TestPass123"
    user = User.register(db_session, user_data)
    db_session.commit()

    assert user.last_login is None
    auth_result = User.authenticate(
        db_session,
        user_data['username'],
        "TestPass123"
    )
    db_session.refresh(user)
    assert user.last_login is not None

def test_user_short_password(db_session):
    """Test error handling in cases of short password submissions"""
    user_data = generate_user_data()
    user_data['password'] = "Tp123"
    with pytest.raises(
        ValueError, 
        match="Password must contain at least six characters"
    ):
        User.register(db_session, user_data)
    db_session.rollback()

def test_user_duplicate_registration(db_session, test_user):
    """Test error handling in cases of existing user records"""
    user_data = generate_user_data()
    user_data['username'] = test_user.username
    user_data['password'] = "TestPass123"

    db_session.add(test_user)
    db_session.commit()
    with pytest.raises(
        ValueError,
        match="Username or email already exists"
    ):
        User.register(db_session, user_data)
    db_session.rollback()

def test_user_bad_auth_credentials(db_session):
    """Tests error handling in case of bad login credentials"""
    assert User.authenticate(db_session, "", "") is None

def test_token_creation_and_validation(db_session):
    """Test token creation and verification"""
    user_data = generate_user_data()
    user_data['password'] = "TestPass123"
    user_data['confirm_password'] = "TestPass123"
    user = User.register(db_session, user_data)
    db_session.commit()

    token = User.create_access_token({"sub": str(user.id)})
    assert token is not None

    decoded_user_id = User.verify_token(token)
    assert decoded_user_id == user.id

def test_invalid_token():
    """Test handling of invalid token strings"""
    invalid_token = "bad.token.string"
    result = User.verify_token(invalid_token)
    assert result is None


