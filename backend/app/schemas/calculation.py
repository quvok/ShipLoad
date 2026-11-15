"""Explicit, source-backed inputs for a preliminary loading calculation."""
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Positive = Annotated[float, Field(gt=0, le=1_000_000_000, allow_inf_nan=False)]
Finite = Annotated[float, Field(ge=-10_000, le=10_000, allow_inf_nan=False)]
SignedMoment = Annotated[float, Field(ge=-1_000_000_000_000, le=1_000_000_000_000, allow_inf_nan=False)]
Source = Annotated[str, Field(min_length=3, max_length=500)]


class CalculationWeight(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    mass_t: Annotated[float, Field(ge=0, le=1_000_000, allow_inf_nan=False)]
    lcg_m: Finite
    tcg_m: Finite
    vcg_m: Finite
    free_surface_moment_tm: Annotated[float, Field(ge=0, le=1_000_000_000_000, allow_inf_nan=False)] = 0
    include_in_forward_strength: bool = True
    source_reference: Source


class CalculationLightship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mass_t: Positive
    lcg_m: Finite
    tcg_m: Finite
    vcg_m: Finite
    source_reference: Source
    forward_strength_moment_tm: SignedMoment | None = None
    strength_source_reference: Source | None = None

    @model_validator(mode="after")
    def strength_source_matches_value(self) -> CalculationLightship:
        if (self.forward_strength_moment_tm is None) != (self.strength_source_reference is None):
            raise ValueError("A lightship strength moment and its source must be supplied together")
        return self


class CalculationHydrostaticRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    displacement_volume_m3: Positive
    draft_extreme_m: Positive
    lcf_from_ap_m: Finite
    lcb_from_ap_m: Finite
    transverse_metacentre_z_m: Annotated[float, Field(gt=0, le=10_000, allow_inf_nan=False)]
    mct_t_m_per_cm: Annotated[float, Field(gt=0, le=1_000_000_000, allow_inf_nan=False)]
    source_reference: Source


class KNPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heel_angle_deg: Annotated[float, Field(ge=0, le=180, allow_inf_nan=False)]
    kn_m: Finite
    source_reference: Source


class LoadingCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vessel_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    vessel_data_revision: str = Field(min_length=1, max_length=80)
    coordinate_convention: str = Field(min_length=10, max_length=500)
    coordinate_source_reference: Source
    lbp_m: Positive
    lbp_source_reference: Source
    seawater_density_t_m3: Annotated[float, Field(gt=0.5, le=1.5, allow_inf_nan=False)]
    seawater_density_source_reference: Source
    lightship: CalculationLightship
    items: list[CalculationWeight] = Field(min_length=1, max_length=2000)
    hydrostatic_table: list[CalculationHydrostaticRow] = Field(min_length=2, max_length=2000)
    kn_curve: list[KNPoint] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def hydrostatic_rows_are_ordered(self) -> LoadingCalculationRequest:
        volumes = [row.displacement_volume_m3 for row in self.hydrostatic_table]
        if volumes != sorted(volumes) or len(volumes) != len(set(volumes)):
            raise ValueError("Hydrostatic displacement volumes must be strictly increasing")
        angles = [point.heel_angle_deg for point in self.kn_curve]
        if self.kn_curve and (
            len(angles) < 2 or angles != sorted(angles) or len(angles) != len(set(angles))
        ):
            raise ValueError("KN curve angles must be strictly increasing and contain at least two points")
        if self.kn_curve and (angles[0] != 0 or abs(self.kn_curve[0].kn_m) > 1e-6):
            raise ValueError("KN curve must start at heel angle 0 with KN=0")
        return self
