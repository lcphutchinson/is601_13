"""This module provides a central interface for accessing global settings"""

from pydantic_settings import BaseSettings
from typing import Optional

class AppSettings(BaseSettings):
    """BaseSettings extender for pydantic and broader app settings"""
    
    DATABASE_URL: str       = "postgresql://postgres:postgres@localhost:5432/fastapi_db"
    JWT_SECRET: str         = "super-secret-key-for-jwt-min-32-chars"
    JWT_REFRESH_SECRET: str = "super-secret-refresh-key-min-32-chars"
    JWT_ALGORITHM: str      = "HS256"
    ACCESS_TOKEN_TTL: int   = 30    # minutes
    REFRESH_TOKEN_TTL: int  = 7     # days
    BCRYPT_ROUNDS: int      = 12

    class Config:
        env_file = ".env"

class GlobalSettings():
    """Singleton wrapper for retrieving the AppSettings object"""
    _settings: AppSettings = None

    def __new__(cls):
        if not cls._settings:
            cls._settings = AppSettings()
        return cls._settings

