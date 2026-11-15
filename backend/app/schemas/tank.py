"""Tank registry schemas. Calibration tables are modelled separately."""
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

TankCode = Annotated[str, Field(min_length=1, max_length=80)]
PositiveCapacityM3 = Annotated[float, Field(gt=0, le=10_000_000, allow_inf_nan=False)]


class TankType(StrEnum):
    BALLAST = "ballast"
    FUEL_OIL = "fuel_oil"
    DIESEL_OIL = "diesel_oil"
    FRESH_WATER = "fresh_water"
    LUBRICATING_OIL = "lubricating_oil"
    SEWAGE = "sewage"
    SLUDGE = "sludge"
    OTHER = "other"


class TankCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tank_code: TankCode
    name: str = Field(min_length=1, max_length=120)
    tank_type: TankType
    nominal_capacity_m3: PositiveCapacityM3 | None = None
    arrangement_source_reference: str = Field(min_length=3, max_length=500)
    capacity_source_reference: str | None = Field(default=None, min_length=3, max_length=500)

    @model_validator(mode="after")
    def capacity_must_be_sourced(self) -> "TankCreate":
        if self.nominal_capacity_m3 is not None and self.capacity_source_reference is None:
            raise ValueError("Nominal capacity requires a source reference")
        return self


class TankRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vessel_id: str
    tank_code: str
    name: str
    tank_type: TankType
    nominal_capacity_m3: PositiveCapacityM3 | None
    arrangement_source_reference: str
    capacity_source_reference: str | None
    data_status: str
