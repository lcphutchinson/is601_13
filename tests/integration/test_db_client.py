"""This module provides a test suite for the DatabaseClient class"""
import pytest

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from app.database_client import DatabaseClient

def test_property_types(test_db):
    """Tests the DatabaseClient's attributes for appropriate typing"""
    assert isinstance(test_db.engine, Engine)
    assert isinstance(test_db.model_base, declarative_base().__class__)
    assert isinstance(test_db.session_agent, sessionmaker)

def test_singleton_properties(test_db):
    """Tests the singleton properties of the DatabaseClient object"""
    test_client = DatabaseClient() # Test Singleton return
    assert test_client is test_db
    assert test_client.session_agent is test_db.session_agent

    DatabaseClient._instance = None
    DatabaseClient._is_configured = False
    test_client = DatabaseClient()
    assert test_client is not test_db
    assert test_client.session_agent is not test_db.session_agent

def test_session_properties(test_db):
    """Verifies the properties of returned Session instances from get_session"""
    session_a = test_db.get_session()
    assert isinstance(next(session_a), Session)
    session_b = test_db.get_session()
    assert session_a is not session_b





    
