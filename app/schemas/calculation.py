"""This module provides a validation schema for IO data related to the calculation model"""
import pydantic as pyd

from enum import Enum
from datetime import datetime
from uuid import UUID
from typing import List, Optional

class CalculationType(str, Enum):
    """Valid Calculation types"""
    ADDITION = "addition"
    SUBTRACTION = "subtraction"
    MULTIPLICATION = "multiplication"
    DIVISION = "division"
    MODULUS = "modulus"

class CalculationForm(pyd.BaseModel):
    """Schema for incoming Calculation forms from the UI"""
    type: CalculationType = pyd.Field(
        ...,
        description="The type of calculation to perform",
        example="addition"
    )
    inputs: List[float] = pyd.Field(
        ...,
        description="Numeric operands for the calculation, as a list",
        example=[8.5, 6, 3.2],
        min_items=2
    )

    @pyd.field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        valid_types = { e.value for e in CalculationType }
        if not isinstance(v, str) or v.lower() not in valid_types:
            raise ValueError(f"Type input invalid")
        return v.lower()

    @pyd.model_validator(mode='after')
    def validate_inputs(self) -> "CalculationForm":
        """Performs type-specific input validation"""
        division_types = [
            CalculationType.DIVISION,
            CalculationType.MODULUS,
            # ROOT would belong here too
        ]
        if self.type in division_types:
            if 0 in self.inputs[1:]:
               raise ValueError("Zero divisor not supported in division-based operations")
        return self

    model_config = pyd.ConfigDict(
        from_attributes=True,
        json_schema_extras={
            "examples": [
                {"type": "addition", "inputs": [8.5, 6, 3.2]},
                {"type": "division", "inputs": [48, 8]},
            ]
        }
    )

class CalculationCreate(CalculationForm):
    """Schema for complete Calculation records for database insertion"""
    user_id: UUID = pyd.Field(
        ...,
        description="UUID of the creating user",
        example="123e4567-e89b-12d3-a456-426614174000",
    )

    model_config = pyd.ConfigDict(
        json_schema_extra={
            "example": {
                "type": "addition",
                "inputs": [8.5, 6, 3.2],
                "user_id": "123e4567-e89b-12d3-a456-426614174000"
            }
        }
    )

class CalculationRecord(CalculationForm):
    """Schema for outgoing Calculation records from the database"""
    id: UUID = pyd.Field(
        ...,
        description="Unique identifier for the Calculation record",
        example="123e4567-e89b-12d3-a456-426614174999"
    )
    user_id: UUID = pyd.Field(
        ...,
        description="Unique identifier for the user associated with this record",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    created_at: datetime = pyd.Field(..., description="Date and Time of this record's entry")
    updated_at: datetime = pyd.Field(..., description="Date and Time of this record's last update")

    model_config = pyd.ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174999",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "type": "addition",
                "inputs": [8.5, 6, 3.2],
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00"
            }
        }
    )

class CalculationUpdate(pyd.BaseModel):
    """Schema for update operations on existing Calculation records"""
    inputs: Optional[List[float]] = pyd.Field(
        None,
        description="Updated input list for the record",
        example=[48, 8],
        min_items=2
    )

    @pyd.model_validator(mode="after")
    def validate_inputs(self) -> "CalculationUpdate":
        """Validate new inputs, if any"""
        if self.inputs and len(self.inputs) < 2:
            raise ValueError("Calculation requires at least 2 operands")
        return self

    model_config = pyd.ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": {"inputs": [48, 8]}}
    )

