"""This module provides a test swuite for the Calculation object family"""

import logging as logs
import pytest

from sqlalchemy.exc import IntegrityError
from uuid import uuid4

from app.models.calculation import Calculation
from app.models.user import User
from tests.conftest import managed_db_session

logger = logs.getLogger(__name__)

def test_calculation_properties(test_user, db_session):
    """
    Verifies basic creation and deletion cascade functionality
    - Create a single calculation associated with a user and verify its fields
    - Delete the associated user and verify cascade deletion
    """
    new_calc = Calculation.create(
        "addition",
        user_id=test_user.id,
        inputs=[1, 2]
    )
    db_session.add(new_calc)
    db_session.commit()
    
    user_record = db_session.query(User).filter_by(email=test_user.email).first()
    calc_record = db_session.query(Calculation).filter_by(user_id=test_user.id).first()
    assert calc_record is not None, \
        "test_calculation_properties failure: new_calc not inserted"
    assert calc_record.user_id == user_record.id
    assert calc_record.type == 'addition'
    assert 1 in calc_record.inputs
    assert 2 in calc_record.inputs

    db_session.delete(test_user)
    db_session.commit()

    calc_record = db_session.query(Calculation).filter_by(id=calc_record.id).first()
    assert calc_record is None, \
        "test_calculation_properties failure: calc_record delete cascade failed"
    
def test_calculation_foreign_key_constraint(test_user, db_session):
    """Tests error handling in cases of incorrect/missing user relations"""
    db_session.delete(test_user)
    db_session.commit()
    new_calc = Calculation.create(
        "addition",
        user_id=test_user.id,
        inputs=[1, 2]
    )
    db_session.add(new_calc)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

