"""This module provides the ORM logic for the calculation record database model"""

import uuid

from abc import abstractmethod
from datetime import datetime, timezone
from functools import reduce
from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app import ModelBase

def aware_now():
    """Helper function that returns zimezone aware datetime.now"""
    return datetime.now(timezone.utc)

class Calculation(ModelBase):
    """Abstract Base Class for the Calculation family data model"""
    __tablename__ = 'calculations'
    _types : dict[str, type] = {}

    id          = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(PG_UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    type        = Column(String(50), nullable=False)
    inputs      = Column(JSON, nullable=False)
    created_at  = Column(DateTime, default=aware_now, nullable=False)
    updated_at  = Column(DateTime, default=aware_now, onupdate=aware_now, nullable=False)

    user = relationship("User", back_populates="calculations")

    __mapper_args__ = {
        "polymorphic_on": type,
        "polymorphic_identity": "calculation",
        "with_polymorphic": "*",
    }

    @classmethod
    def create(cls, calc_type: str,
               user_id: uuid.UUID, inputs: list[float]) -> 'Calculation':
        """
        Factory Creation method for the Calculation family of model objects
        
        Parameters
        ----------
        calc_type: str
            a string tag identifying the Calculation subclass to create
        user_id: uuid.UUID
            the user.id of the calling User
        inputs: list[float]
            a list of operands to the calculation called

        Raises
        ------
        ValueError
            If the provided type string does not match a registered calculation type
        """
        calc_class = cls._types.get(calc_type.lower())
        if not calc_class:
            raise ValueError(f"Unsupported calculation type: {calc_type}")
        if not inputs or len(inputs) < 2:
            raise ValueError(f"{calc_type} requires at least 2 operands")
        return calc_class(user_id=user_id, inputs=inputs)

    @classmethod
    def register(cls, calc_cls: type) -> type:
        """
        Decorator for Calculation subclass registration

        Parameters
        ----------
        calc_cls: type
            The Calculation subclass to register

        Raises
        ------
        TypeError
            If a class outside the Calculation family is registered
        """
        if not issubclass(calc_cls, Calculation):
            raise TypeError("Registered class must inherit from Calculation")
        cls._types[calc_cls.__name__.lower()] = calc_cls
        return calc_cls

    @abstractmethod
    def get_result(self) -> float:
        """
        Abstract method for resolution on Calculation family objects

        Returns
        -------
        float
            the result of the Calculation
        """
        raise NotImplementedError # pragma: no cover

    def __repr__(self) -> str:
        """
        Produces a simple label describing the Calculation

        Uses the form <Calculation(type=<type>, inputs=[<inputs>])>
        
        Returns
        -------
        str
            A string label for this Calculation
        """
        return f"<Calculation(type={self.type}, inputs={self.inputs})>"

@Calculation.register
class Addition(Calculation):
    """Data model for Addition Calculations"""
    __mapper_args__ = {"polymorphic_identity": "addition"}
    
    def get_result(self) -> float:
        return reduce(lambda x, y: x + y, self.inputs)
        
@Calculation.register
class Subtraction(Calculation):
    """Data model for Subtraction Calculations"""
    __mapper_args__ = {"polymorphic_identity": "subtraction"}
    
    def get_result(self) -> float:
        return reduce(lambda x, y: x - y, self.inputs)

@Calculation.register
class Multiplication(Calculation):
    """Data model for Multiplication Calculations"""
    __mapper_args__ = {"polymorphic_identity": "multiplication"}
    
    def get_result(self) -> float:
        return reduce(lambda x, y: x * y, self.inputs)

@Calculation.register
class Division(Calculation):
    """Data model for Division Calculations"""
    __mapper_args__ = {"polymorphic_identity": "division"}
    
    def get_result(self) -> float:
        if 0 in self.inputs[1:]:
            raise ValueError("Zero divisor input invalid for Division")
        return reduce(lambda x, y: x / y, self.inputs)

@Calculation.register
class Modulus(Calculation):
    """Data model for Modulo Division Calculations"""
    __mapper_args__ = {"polymorphic_identity": "modulus"}
    
    def get_result(self) -> float:
        if 0 in self.inputs[1:]:
            raise ValueError("Zero divisor input invalid for Modulo Division")
        return reduce(lambda x, y: x % y, self.inputs)

