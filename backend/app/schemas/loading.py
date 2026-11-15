"""Loading-condition input schemas.

Masses and coordinates are explicit SI values. The API never derives mass
from tank volume unless a separately reviewed density conversion is added.
"""
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

PositiveMassKg = Annotated[float, Field(gt=0, le=1_000_000_000, allow_inf_nan=False)]
CoordinateM = Annotated[float, Field(allow_inf_nan=False, ge=-10_000, le=10_000)]


class LoadingItemKind(StrEnum):
    LIGHTSHIP = "lightship"
    CARGO = "cargo"
    BALLAST = "ballast"
    FUEL_OIL = "fuel_oil"
    DIESEL_OIL = "diesel_oil"
    FRESH_WATER = "fresh_water"
    LUBRICATING_OIL = "lubricating_oil"
    STORES = "stores"
    CREW_AND_EFFECTS = "crew_and_effects"
    OTHER = "other"


class WeightPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x_m: CoordinateM
    y_m: CoordinateM
    z_m: CoordinateM
    position_source: str = Field(min_length=3, max_length=500)


class LoadingItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=240)
    kind: LoadingItemKind
    mass_kg: PositiveMassKg
    position: WeightPosition | None = None
    tank_id: str | None = Field(default=None, min_length=1, max_length=80)
    source_reference: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def require_position_or_tank(self) -> "LoadingItemCreate":
        if (self.position is None) == (self.tank_id is None):
            raise ValueError("Provide exactly one of position or tank_id")
        if self.kind in {LoadingItemKind.BALLAST, LoadingItemKind.FUEL_OIL,
                         LoadingItemKind.DIESEL_OIL, LoadingItemKind.FRESH_WATER,
                         LoadingItemKind.LUBRICATING_OIL} and self.tank_id is None:
            raise ValueError("Liquid consumables must reference a defined tank")
        if self.kind == LoadingItemKind.LIGHTSHIP and self.tank_id is not None:
            raise ValueError("Lightship must use a documented position or approved lightship model")
        return self


class LoadingConditionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vessel_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    vessel_data_revision: str = Field(min_length=1, max_length=80)
    items: list[LoadingItemCreate] = Field(min_length=1, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def unique_item_ids(self) -> "LoadingConditionCreate":
        ids = [item.item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("item_id values must be unique within a loading condition")
        return self
