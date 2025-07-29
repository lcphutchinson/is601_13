"""This module provides the ORM logic for the User database model"""

import uuid

from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, relationship
from typing import Any, Dict, Optional

from app import ModelBase
from app.database_client import DatabaseClient
from app.schemas.user_form import UserCreate
from app.schemas.user import UserRecord, AuthToken
from app.settings import GlobalSettings

def aware_now():
    """Helper function that returns zimezone aware datetime.now"""
    return datetime.now(timezone.utc)

class User(ModelBase):
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    __tablename__ = 'users'

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username    = Column(String(50), unique=True, nullable=False, index=True)
    email       = Column(String(120), unique=True, nullable=False, index=True)
    password    = Column(String(255), nullable=False)

    first_name  = Column(String(50), nullable=False)
    last_name   = Column(String(50), nullable=False)
    
    is_active   = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    created_at  = Column(DateTime, default=aware_now, nullable=False)
    updated_at  = Column(DateTime, default=aware_now, 
        onupdate=aware_now(), nullable=False
    )
    last_login  = Column(DateTime, nullable=True)

    calculations = relationship(
        "Calculation",
        back_populates="user",
        cascade="all, delete, delete-orphan"
    )
    
    def __repr__(self):
        """
        Produces a label for the User object using its name and email fields

        Returns
        -------
        str
            An record label for this User
        """
        return f"<User(name= {self.first_name} {self.last_name}, email= {self.email})>"

    @classmethod
    def hash_password(cls, password: str) -> str:
        """
        Hash a password using bcrypt.

        Parameters
        ----------
        password: str
            a plain-text password string

        Returns
        -------
        str
            a bcrypt-hashed string
        """
        return cls._pwd_context.hash(password)

    def verify_password(self, plain_password: str) -> bool:
        """
        Verify a plaintext password against the stored hash.

        Parameters
        ----------
        plain_password: str
            an incoming password from the user login form

        Returns
        -------
        bool
            True if the incoming password is a match
        """
        return self._pwd_context.verify(plain_password, self.password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Creates a JWT access token.

        Parameters
        ----------
        data: dict
            a dictionary containing a JWT token subject
        expires_delta: Optional[timedelta]
            a time-to-live value for this token.

        Returns
        -------
        str
            An encoded jwt string
        """
        settings = GlobalSettings()
        to_encode = data.copy()
        expire = aware_now() + \
            (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_TTL))
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode, 
            settings.JWT_SECRET, 
            algorithm=settings.JWT_ALGORITHM
        )

    @staticmethod
    def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Creates a JWT refresh token.

        Parameters
        ----------
        data: dict
            a dictionary containing a JWT token subject
        expires_delta: Optional[timedelta]
            a time-to-live value for this token.

        Returns
        -------
        str
            An encoded jwt string
        """
        settings = GlobalSettings()
        to_encode = data.copy()
        expire = aware_now() + \
            (expires_delta or timedelta(days=settings.REFRESH_TOKEN_TTL))
        to_encode.update({"exp": expire})
        return jwt.encode(
            to_encode,
            settings.JWT_REFRESH_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )

    @staticmethod
    def verify_token(token: str) -> Optional[UUID]:
        """
        Decodes an verifies a JWT token

        Parameters
        ----------
        token: str
            an encoded JWT string

        Return
        ------
        Optional[UUID]
            The UUID associated with this token, if it exists
        """
        settings = GlobalSettings()
        try:
            payload = jwt.decode(
                    token,
                    settings.JWT_SECRET,
                    algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get("sub")
            return uuid.UUID(user_id) if user_id else None
        except (JWTError, ValueError):
            return None

    @classmethod
    def register(cls, db, user_data: Dict[str, Any]) -> "User":
        """
        Produces a User and adds it to the database session as a user record

        Parameters
        ----------
        db: sqlalchemy.orm.Session
            A database Session instance for this operation
        user_data: Dict[str, Any]
            A dictionary of user inputs from the registration form

        Raises
        ------
        ValueError
            If user inputs do not meet registration constraints

        Returns
        -------
        A newly constructed User object
        """
        try:
            # Input Validation
            password = user_data.get('password', '')
            if len(password) < 6:
                raise ValueError("Password must contain at least six characters")

            existing_user = db.query(cls).filter(
                (cls.email == user_data.get('email')) |
                (cls.username == user_data.get('username'))
            ).first()

            if existing_user:
                raise ValueError("Username or email already exists")

            user_create = UserCreate.model_validate(user_data)

            # Create Operation
            new_user = cls(
                first_name=user_create.first_name,
                last_name=user_create.last_name,
                email=user_create.email,
                username=user_create.username,
                password=cls.hash_password(user_create.password),
                is_active=True,
                is_verified=False
            )

            db.add(new_user)
            db.flush()
            return new_user

        except ValidationError as e: # pragma: no cover
            raise ValueError(str(e))
        except ValueError:
            raise

    @classmethod
    def authenticate(cls, db, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate user login information and optionally return an Auth token

        Parameters
        ----------
        db: sqlalchemy.orm.Session
            A database Session instance for this operation
        username: str
            user input from the username field
        password: str
            user input from the password field

        Returns
        -------
        Optional[Dict[str, Any]]
            An Authorization token for this user
        """
        settings = GlobalSettings()
        
        user = db.query(cls).filter(
            (cls.username == username) | (cls.email == username)
        ).first()

        if not user or not user.verify_password(password):
            return None

        user.last_login = aware_now()
        db.commit()

        user_record = UserRecord.model_validate(user)
        auth_token = AuthToken(
            access_token=cls.create_access_token({"sub": str(user.id)}),
            refresh_token=cls.create_refresh_token({"sub": str(user.id)}),
            token_type="bearer",
            expires_at=aware_now() + timedelta(
                minutes=settings.ACCESS_TOKEN_TTL),
            user=user_record
        )

        return auth_token.model_dump()

