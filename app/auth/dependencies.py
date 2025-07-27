"""This module provides dependency functions for Authorization with fastapi"""

from fastapi import Depends, HTTPException, status

from app.auth import oauth2_token_scheme
from app.models.user import User
from app.schemas.user import UserRecord

def get_current_user(db, token:str = Depends(oauth2_token_scheme)) -> UserRecord:
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

    user_id = User.verify_token(token)
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return UserRecord.model_validate(user)

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

