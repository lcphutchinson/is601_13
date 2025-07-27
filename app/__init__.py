"""This module provides an app-wide ModelBase for classes implementing sqlalchemy"""

from sqlalchemy.orm import declarative_base

ModelBase = declarative_base()
