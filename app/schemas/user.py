"""This module provides a data model for the user-related output records, including Auth tokens"""
import pydantic as pyd

from datetime import datetime
from typing import Optional
from uuid import UUID

class UserRecord(pyd.BaseModel):
    """User record schema for Read operations"""
    id: UUID
    username: str
    email: pyd.EmailStr
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = pyd.ConfigDict(from_attributes=True)

class AuthToken(pyd.BaseModel):
    """Auth Token schema for cookie passing"""
    access_token: str   = pyd.Field(..., description="JWT access token")
    refresh_token: str  = pyd.Field(..., description="JWT refresh token")
    token_type: str     = pyd.Field(default="bearer", description="Token type")
    expires_at: datetime= pyd.Field(..., description="Token expiration timestamp")
    user: UserRecord    = pyd.Field(..., description="User data associated with this token")

    model_config = pyd.ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "refresh_token": "yfXoRu9zdd4PsdVg0dSMfZLxVjNG0nzrHVNK...",
                "token_type": "bearer",
                "expires_at": "2025-10-08T00:00:00",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "janedoe",
                    "email": "jane.doe@example.com",
                    "first_name": "Jane",
                    "last_name": "Doe",
                    "is_active": True,
                    "is_verified": False,
                    "created_at": "2025-07-01T00:00:00",
                    "updated_at": "2025-07-08T00:00:00",
                },
            }
        }
    )

class AuthData(pyd.BaseModel):
    """Data Schema for JWT encoded tokens"""
    user_id: Optional[UUID] = pyd.Field(..., description="User ID for token holder")
    exp: datetime           = pyd.Field(..., description="Timestamp for token expiration")
    jti: str                = pyd.Field(..., description="Token identifier")
    token_type: str         = pyd.Field(..., description="Token type")

    model_config = pyd.ConfigDict(from_attributes=True)

class UserLoginFormat(pyd.BaseModel):
    """Login sample schema for populating login fields"""
    username: str = pyd.Field(
        ...,
        min_length=3,
        max_length=50,
        example="janedoe",
        description="Username or email"
    )
    password: str = pyd.Field(
        ...,
        min_length=8,
        max_length=128,
        example="SecurePass123",
        desciption="Password"
    )

    model_config = pyd.ConfigDict(
        json_schema_extra={
            "example": {
                "username": "janedoe",
                "password": "SecurePass123",
            }
        }
    )
