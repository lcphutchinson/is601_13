"""This module provides a data model for user-related input forms and user record creation"""
import pydantic as pyd

from typing import Optional
from uuid import UUID
from datetime import datetime

class UserForm(pyd.BaseModel):
    """User creation form schema with common fields."""
    first_name: str = pyd.Field(
        min_length=1,
        max_length=50, 
        example="Jane",
        description="First name"
    )
    last_name: str = pyd.Field(
        min_length=1,
        max_length=50,
        example="Doe",
        description="Last name"
    )
    email: pyd.EmailStr = pyd.Field(
        example="jane.doe@example.com",
        description="Email address"
    )
    username: str = pyd.Field(
        min_length=1,
        max_length=50,
        example="janedoe",
        description="Username"
    )
    model_config = pyd.ConfigDict(from_attributes=True)

class PasswordMixin(pyd.BaseModel):
    """Mixin for password validation"""
    password: str = pyd.Field(
        min_length=1,
        max_length=128,
        example="SecurePass123",
        description="Password"
    )

    @pyd.model_validator(mode="before")
    @classmethod
    def validate_password(cls, values: dict) -> dict:
        password = values.get("password")
        if not password:
            raise ValueError("Password is required")
        if len(password) < 8:
            raise ValueError("Password must contain at least 8 characters")
        if not any(char.isupper() for char in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in password):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char.isdigit() for char in password):
            raise ValueError("Password must contain at least one digit")
        return values

class UserLoginForm(pyd.BaseModel):
    """User Login form schema with username/password"""
    username: str = pyd.Field(
        description="Username or email",
        min_length=1,
        max_length=50,
        example="janedoe",
    )
    password: str = pyd.Field(
        ...,
        description="Password",
        min_length=1,
        max_length=128,
        example="SecurePass123"
    )

    model_config = pyd.ConfigDict(
        json_schema_extra={
            "example": {
                "username": "janedoe",
                "password": "SecurePass123"
            }
        }
    )

class UserCreate(UserForm, PasswordMixin):
    """Formatted schema for User Create actions"""
    confirm_password: str = pyd.Field(
            min_length=1,
            max_length=128,
            example="SecurePass123",
            description="Confirm password"
    )
    @pyd.model_validator(mode="after")
    def validate_confirm_password(self) -> "UserCreate":
        if self.password != self.confirm_password:
            raise ValueError("Password inputs do not match")
        return self
   
class UserUpdate(pyd.BaseModel):
    """Schema for User update forms"""
    first_name: str = pyd.Field(
        min_length=1,
        max_length=50,
        example="Jane",
        description="First name"
    )
    last_name: str = pyd.Field(
        min_length=1,
        max_length=50,
        example="Doe",
        description="Last name"
    )
    email: pyd.EmailStr = pyd.Field(
        example="jane.doe@example.com",
        description="Email address"
    )
    username: str = pyd.Field(
        min_length=1,
        max_length=50,
        example="janedoe",
        description="Username"
    )
    
class PasswordUpdate(PasswordMixin):
    """Schema for User password updates"""
    current_password: str = pyd.Field(
        ...,
        min_length=1,
        max_length=128,
        example="OldPass123",
        description="Current password"
    )
    confirm_password: str = pyd.Field(
        ...,
        min_length=1,
        max_length=128,
        example="SecurePass123",
        description="Confirm password"
    )

    @pyd.model_validator(mode='after')
    def validate_new_password(self) -> "PasswordUpdate":
        if self.password != self.confirm_password:
            raise ValueError("Password inputs do not match")
        if self.current_password == self.password:
            raise ValueError("New password cannot match current password")
        return self

    model_config = pyd.ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "current_password": "OldPass123",
                "password": "NewPass123",
                "confirm_password": "NewPass123",
            }
        }
    )


