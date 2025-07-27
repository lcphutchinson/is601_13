"""This module provides a test suite for User model processes on the database"""
import pytest
import logging as logs

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from tests.conftest import generate_user_data, managed_db_session

logger = logs.getLogger(__name__)

def test_database_connection(db_session):
    """Verify basic database connectivity before testing"""
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1
    logger.info("Database connection test passed")

def test_user_create_operation(db_session):
    """
    Verifies basic creation and rollback functionality
    - Creates a single user and validates its fields against seed data
    - Creates a second user with duplicate email address
    - Ensures second user is rejected and rollback does not harm first record
    """
    initial_count = db_session.query(User).count()
    logger.info(f"Initial user count {initial_count} before test_create_operation")
    
    logger.info("Beginning test_create_operation Step 1: Valid User Create")
    user_1_data = generate_user_data()
    user_1 = User(**user_1_data)
    db_session.add(user_1)
    db_session.commit()
    logger.info(f"Added Step 1 test user")

    record_1 = db_session.query(User).filter_by(email=user_1.email).first()
    assert record_1 is not None, \
        "test_user_create_operation Step 1 Failure: user_1 not inserted" 
    assert record_1.first_name == user_1_data['first_name'] and \
        record_1.last_name == user_1_data['last_name'] and \
        record_1.email == user_1_data['email'] and \
        record_1.username == user_1_data['username'] and \
        record_1.password == user_1.password, \
        "test_user_create_operation Step 1 Failure: user_1 fields improperly stored."
    
    post_create_count = db_session.query(User).count()
    assert post_create_count == initial_count + 1, (
        "test_user_create_operation Step 1 Unintended Side Effect: "
        f"{post_create_count - initial_count} User differential"
    )

    logger.info(f"Step 1 Successful. Beginning Step 2: Duplicate User Create")
    user_2_data = generate_user_data()
    user_2_data['email'] = user_1_data['email']
    logger.info("Step 2 test user created with duplicate email address")
    try:
        logger.info("Attempting insert...")
        user_2 = User(**user_2_data)
        db_session.add(user_2)
        db_session.commit()
        assert False, \
            "test_user_create_operation Step 2 Failure: unique email constraint failed"
    except IntegrityError:
        db_session.rollback()
        logger.info("IntegrityError thrown: rolling back")

    record_2 = db_session.query(User).filter_by(email=user_1.email).first()
    assert record_2 is not None, \
        "test_user_create_operation Step 2 Failure: user_1 deleted in rollback"
    assert record_2.username == user_1_data['username'], \
        "test_user_create_operation Step 2 Failure: user_1 altered during Step 2"
    post_rollback_count = db_session.query(User).count()
    assert post_rollback_count == post_create_count, (
        "test_user_create_operation Step 2 Unintended Side Effect:"
        f"{post_create_count} User differential should be 0"
    )

def test_concurrent_user_create(db_session):
    """Tests multiple insertions"""
    initial_count = db_session.query(User).count()
    users = []
    for _ in range(3):
        user_data = generate_user_data()
        user = User(**user_data)
        users.append(user)
        db_session.add(user)

    db_session.commit()
    post_create_count = db_session.query(User).count()
    assert post_create_count == initial_count + 3, (
        "Concurrent user creation yielded user differential"
        f"{post_create_count - initial_count}, expected 3"
    )

def test_user_create_unique_constraints(db_session):
    """Tests the unique username and unique email constraints"""
    user_1_data = generate_user_data()
    user_2_data = generate_user_data()
    user_3_data = generate_user_data()
    user_1_data['username'] = user_2_data['username']
    user_1_data['email'] = user_3_data['email']
    user_1 = User(**user_1_data)
    user_2 = User(**user_2_data)
    user_3 = User(**user_3_data)

    db_session.add(user_1)
    db_session.commit()

    db_session.add(user_2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(user_3)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

@pytest.mark.parametrize(
    "null_field", [
        ("first_name"),
        ("last_name"),
        ("email"),
        ("username"),
        ("password"),
    ]
)
def test_user_create_null_constraints(null_field: str, db_session):
    """Tests error handling in cases of null input fields"""
    user_data = generate_user_data()
    user_data.pop(null_field)
    user = User(**user_data)
    db_session.add(user)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_user_model_representation(test_user):
    """Test the string representation of User model"""
    expected = f"<User(name= {test_user.first_name} {test_user.last_name}, email= {test_user.email})>"
    assert str(test_user) == expected
