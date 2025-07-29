"""This module provides dependency functions for Authorization with fastapi"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.auth import oauth2_token_scheme
from app.database_client import DatabaseClient
from app.models.user import User
from app.schemas.user import UserRecord

def get_current_user(
        db: Session = Depends(DatabaseClient().get_session),
        token:str = Depends(oauth2_token_scheme)) -> UserRecord:
    """
    Dependency to get current user from JWT token.
    
    Parameters
    ----------
    db: sqlalchemy.orm.Session
        A database Session instance for this operation
    token: str
        An authorization token passed from the remote user

    Raises
    ------
    HTTPException
        if the passed token does not correspond to a user

    Returns
    -------
    UserRecord
        A record of the authenticated user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token_data = User.verify_token(token)
    if not token_data:
        raise credentials_exception
    if isinstance(token_data, dict):
        user_data = token_data.get("user")
        if user_data:
            return UserRecord.model_validate(user_data)
        user_data = token_data.get("sub")
        if user_data:
            user = db.query(User).filter(User.id == user_data).first()
            if user:
                return UserRecord.model_validate(user)
        raise credentials_exception
    if isinstance(token_data, UUID):
        user = db.query(User).filter(User.id == token_data).first()
        if user:
            return UserRecord.model_validate(user)
        raise credentials_exception

def get_current_active_user(
    current_user: UserRecord = Depends(get_current_user)
    ) -> UserRecord:
    """
    Dependency to filter returned user by activity status

    Parameters
    ----------
    current_user: UserRecord
        a database record for screening

    Raises
    ------
    HTTPException
        if the user is inactive

    Returns
    -------
    UserRecord
        the validated database record
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

