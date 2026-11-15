"""Validated API schemas for vessel identity and reference conventions.

These schemas intentionally do not provide default technical particulars.
All dimensions and coordinate conventions must be supplied from vessel sources.
"""
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VesselType(StrEnum):
    GENERAL_CARGO = "general_cargo"
    CONTAINER = "container"
    BULK_CARRIER = "bulk_carrier"
    TANKER = "tanker"
    MULTIPURPOSE = "multipurpose"
    OTHER = "other"


class AxisDirection(StrEnum):
    POSITIVE_FORWARD = "positive_forward"
    POSITIVE_AFT = "positive_aft"
    POSITIVE_PORT = "positive_port"
    POSITIVE_STARBOARD = "positive_starboard"
    POSITIVE_UP = "positive_up"
    POSITIVE_DOWN = "positive_down"


class CoordinateConvention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    origin_description: str = Field(min_length=5, max_length=500)
    x_axis_direction: AxisDirection
    y_axis_direction: AxisDirection
    z_axis_direction: AxisDirection
    vertical_datum_description: str = Field(min_length=3, max_length=500)


class VesselCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    vessel_type: VesselType
    loa_m: float = Field(gt=0, le=1000)
    lbp_m: float = Field(gt=0, le=1000)
    moulded_breadth_m: float = Field(gt=0, le=250)
    moulded_depth_m: float = Field(gt=0, le=150)
    coordinate_convention: CoordinateConvention

    @model_validator(mode="after")
    def validate_principal_dimensions(self) -> "VesselCreate":
        if self.lbp_m > self.loa_m:
            raise ValueError("LBP cannot exceed LOA")
        if self.moulded_breadth_m > self.loa_m:
            raise ValueError("Moulded breadth cannot exceed LOA")
        return self
