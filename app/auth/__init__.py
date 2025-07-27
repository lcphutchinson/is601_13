"""This module provides an importable global oauth2 scheme setting"""
from fastapi.security import OAuth2PasswordBearer

oauth2_token_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
oauth2_json_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
