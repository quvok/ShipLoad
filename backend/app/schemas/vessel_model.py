"""Data-driven vessel model schemas shared by every vessel type.

Vessel type is descriptive metadata, not a switch that invents geometry or
stability data. A bulk carrier, tanker or container ship is modelled from its
own documented spaces, hydrostatics and approved limits.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Finite = Annotated[float, Field(allow_inf_nan=False)]


class CompartmentKind(StrEnum):
    CARGO_HOLD = "cargo_hold"
    CARGO_TANK = "cargo_tank"
    BALLAST_TANK = "ballast_tank"
    FUEL_TANK = "fuel_tank"
    FRESH_WATER_TANK = "fresh_water_tank"
    OTHER_TANK = "other_tank"
    VOID_SPACE = "void_space"
    OTHER = "other"


class SourceReference(BaseModel):
    """Auditable source location for a model datum."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1, max_length=80)
    document_name: str = Field(min_length=1, max_length=255)
    page: int = Field(ge=1)
    location: str = Field(min_length=1, max_length=300)
    excerpt: str | None = Field(default=None, max_length=2000)


class CapacityPoint(BaseModel):
    """A point on a sounding/ullage/capacity or hold calibration curve."""

    model_config = ConfigDict(extra="forbid")

    filling_parameter: Finite
    volume_m3: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    lcg_m: Finite
    tcg_m: Finite
    vcg_m: Finite
    free_surface_moment_tm: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 0
    source: SourceReference


class CompartmentDefinition(BaseModel):
    """Generic cargo space or tank; applicable to tankers and dry cargo ships."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    kind: CompartmentKind
    maximum_volume_m3: Positive | None = None
    maximum_mass_t: Positive | None = None
    permitted_cargo_types: list[str] = Field(default_factory=list, max_length=100)
    capacity_curve: list[CapacityPoint] = Field(default_factory=list, max_length=500)
    arrangement_source: SourceReference
    capacity_source: SourceReference | None = None

    @model_validator(mode="after")
    def validate_capacity_data(self) -> "CompartmentDefinition":
        if self.capacity_curve and self.capacity_source is None:
            raise ValueError("A capacity curve requires its source reference")
        if self.maximum_volume_m3 is not None and self.capacity_curve:
            if max(point.volume_m3 for point in self.capacity_curve) > self.maximum_volume_m3 + 1e-6:
                raise ValueError("Capacity curve exceeds documented maximum volume")
        if self.capacity_curve:
            parameters = [point.filling_parameter for point in self.capacity_curve]
            if parameters != sorted(parameters) or len(parameters) != len(set(parameters)):
                raise ValueError("Capacity-curve filling parameters must be strictly increasing")
        return self


class HydrostaticRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    displacement_volume_m3: Positive
    draft_extreme_m: Positive
    lcf_from_origin_m: Finite
    lcb_from_origin_m: Finite
    km_transverse_m: Positive
    mct_t_m_per_cm: Positive
    source: SourceReference


class StabilityCurvePoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heel_angle_deg: Annotated[float, Field(ge=0, le=180, allow_inf_nan=False)]
    righting_arm_m: Finite
    source: SourceReference


class LongitudinalStrengthLimit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    station: str = Field(min_length=1, max_length=80)
    maximum_shear_force_t: Positive | None = None
    minimum_shear_force_t: Positive | None = None
    maximum_bending_moment_tm: Positive | None = None
    minimum_bending_moment_tm: Positive | None = None
    source: SourceReference


class VesselCalculationModel(BaseModel):
    """Source-backed model; optional datasets remain explicitly unavailable."""

    model_config = ConfigDict(extra="forbid")

    vessel_id: str = Field(min_length=1, max_length=80)
    vessel_type: str = Field(min_length=1, max_length=40)
    lbp_m: Positive | None = None
    breadth_m: Positive | None = None
    coordinate_convention: dict[str, str] | None = None
    compartments: list[CompartmentDefinition] = Field(default_factory=list, max_length=1000)
    hydrostatics: list[HydrostaticRow] = Field(default_factory=list, max_length=2000)
    stability_curve: list[StabilityCurvePoint] = Field(default_factory=list, max_length=1000)
    strength_limits: list[LongitudinalStrengthLimit] = Field(default_factory=list, max_length=500)
    lightship_mass_t: Positive | None = None
    lightship_lcg_m: Finite | None = None
    lightship_tcg_m: Finite | None = None
    lightship_vcg_m: Finite | None = None
    lightship_source: SourceReference | None = None

    @model_validator(mode="after")
    def validate_model_consistency(self) -> "VesselCalculationModel":
        codes = [space.code for space in self.compartments]
        if len(codes) != len(set(codes)):
            raise ValueError("Compartment codes must be unique within a vessel")
        if self.hydrostatics:
            volumes = [row.displacement_volume_m3 for row in self.hydrostatics]
            if volumes != sorted(volumes) or len(volumes) != len(set(volumes)):
                raise ValueError("Hydrostatic displacement volumes must be strictly increasing")
        if self.stability_curve:
            angles = [point.heel_angle_deg for point in self.stability_curve]
            if angles != sorted(angles) or len(angles) != len(set(angles)):
                raise ValueError("Stability curve heel angles must be strictly increasing")
        lightship_values = (
            self.lightship_mass_t, self.lightship_lcg_m, self.lightship_tcg_m,
            self.lightship_vcg_m, self.lightship_source,
        )
        if any(value is not None for value in lightship_values) and not all(
            value is not None for value in lightship_values
        ):
            raise ValueError("Lightship data must be supplied as a complete sourced set")
        return self


def assess_model_capabilities(model: VesselCalculationModel) -> dict[str, object]:
    """Report calculable domains from available data, never from vessel-type guesses."""
    checks = {
        "weight_moments": all(value is not None for value in (
            model.lightship_mass_t, model.lightship_lcg_m,
            model.lightship_tcg_m, model.lightship_vcg_m,
        )),
        "draft_and_trim": bool(model.hydrostatics and model.lbp_m),
        "tank_or_hold_loading": any(space.capacity_curve for space in model.compartments),
        "initial_stability": bool(model.hydrostatics and model.lightship_vcg_m is not None),
        "large_angle_stability": bool(model.stability_curve),
        "longitudinal_strength": bool(model.strength_limits),
    }
    return {
        "vessel_id": model.vessel_id,
        "vessel_type": model.vessel_type,
        "capabilities": checks,
        "available": [name for name, ready in checks.items() if ready],
        "missing": [name for name, ready in checks.items() if not ready],
        "compartment_count": len(model.compartments),
        "compartment_kinds": sorted({space.kind.value for space in model.compartments}),
        "status": "READY_FOR_REVIEW" if all(checks.values()) else "INCOMPLETE_MODEL",
        "note": "Capability status is based on supplied datasets, not vessel type. Every input still requires source review.",
    }
