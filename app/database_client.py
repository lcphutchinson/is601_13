"""This module provides an interface for database connection functionality, usable in queries"""
import logging as logs

from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from app import ModelBase
from app.settings import GlobalSettings

class DatabaseClient():
    """Singleton Wrapper object for SQLAlchemy connection configurations"""
    _instance: 'DatabaseClient' = None
    _is_configured: bool = False

    def __new__(cls) -> 'DatabaseClient': 
        if not cls._instance:
            cls._instance = super(DatabaseClient, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """
        Configures the initial database connection

        Raises
        ------
        SQLAlchemyError
            if the initial SQLAlchemy Engine creation fails
        """
        if self._is_configured:
            return
        try:
            self.engine = create_engine(GlobalSettings().DATABASE_URL, echo=True)
        except SQLAlchemyError as e: # pragma: no cover
            logs.critical(f"Error creating SQLAlchemy Engine: {e}")
            raise
        self.model_base = ModelBase
        self.session_agent = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        self._is_configured = True

    def get_session(self):
        """
        Dependency function for mediating database access

        Yields
        ------
        Session
            A SQLAlchemy Session instance using the client's connection
        """
        session = self.session_agent()
        try:
            yield session
        finally: # pragma: no cover
            session.close()

