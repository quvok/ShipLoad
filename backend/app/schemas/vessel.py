"""Validated API schemas for vessel identity and reference conventions."""
from datetime import datetime
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
    loa_m: float | None = Field(default=None, gt=0, le=1000, allow_inf_nan=False)
    lbp_m: float | None = Field(default=None, gt=0, le=1000, allow_inf_nan=False)
    moulded_breadth_m: float | None = Field(default=None, gt=0, le=250, allow_inf_nan=False)
    moulded_depth_m: float | None = Field(default=None, gt=0, le=150, allow_inf_nan=False)
    coordinate_convention: CoordinateConvention | None = None

    @model_validator(mode="after")
    def validate_principal_dimensions(self) -> "VesselCreate":
        if self.lbp_m is not None and self.loa_m is not None and self.lbp_m > self.loa_m:
            raise ValueError("LBP cannot exceed LOA")
        if self.moulded_breadth_m is not None and self.loa_m is not None and self.moulded_breadth_m > self.loa_m:
            raise ValueError("Moulded breadth cannot exceed LOA")
        return self


class VesselRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    vessel_type: VesselType
    loa_m: float | None
    lbp_m: float | None
    moulded_breadth_m: float | None
    moulded_depth_m: float | None
    coordinate_convention: CoordinateConvention | None
    data_status: str
    created_at: datetime
