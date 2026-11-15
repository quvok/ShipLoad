"""Deterministic loading-condition and hydrostatic calculations.

The equations implemented here reproduce the method written in the user's
course project, sections 2–5. They are not a substitute for the approved
stability booklet, class criteria, or an approved ship loading instrument.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


class CalculationInputError(ValueError):
    """Raised when required inputs are missing, invalid, or outside source data."""


@dataclass(frozen=True)
class WeightItem:
    """One weight in a loading condition; coordinates are metres from AP/CL/BL."""

    name: str
    mass_t: float
    lcg_m: float
    tcg_m: float
    vcg_m: float
    free_surface_moment_tm: float = 0.0
    include_in_forward_strength: bool = True


@dataclass(frozen=True)
class Lightship:
    mass_t: float
    lcg_m: float
    tcg_m: float
    vcg_m: float
    forward_moment_tm: float


@dataclass(frozen=True)
class HydrostaticPoint:
    """One approved hydrostatic-table row; Xf and Xc are measured from AP."""

    displacement_volume_m3: float
    draft_extreme_m: float
    lcf_from_ap_m: float
    lcb_from_ap_m: float
    transverse_metacentre_z_m: float
    mct_t_m_per_cm: float


def _finite_positive(value: float, name: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise CalculationInputError(f"{name} must be a finite positive number")


def interpolate_hydrostatics(
    displacement_volume_m3: float,
    table: Sequence[HydrostaticPoint],
) -> HydrostaticPoint:
    """Linearly interpolate between adjacent rows; never extrapolate."""
    _finite_positive(displacement_volume_m3, "displacement_volume_m3")
    if len(table) < 2:
        raise CalculationInputError("At least two hydrostatic rows are required")
    rows = sorted(table, key=lambda row: row.displacement_volume_m3)
    for row in rows:
        _finite_positive(row.displacement_volume_m3, "hydrostatic displacement volume")
        _finite_positive(row.mct_t_m_per_cm, "MCT")
        if not all(math.isfinite(value) for value in (
            row.draft_extreme_m,
            row.lcf_from_ap_m,
            row.lcb_from_ap_m,
            row.transverse_metacentre_z_m,
        )):
            raise CalculationInputError("Hydrostatic table contains a non-finite value")
    if displacement_volume_m3 < rows[0].displacement_volume_m3 or displacement_volume_m3 > rows[-1].displacement_volume_m3:
        raise CalculationInputError("Displacement is outside hydrostatic table; extrapolation is prohibited")
    for row in rows:
        if math.isclose(displacement_volume_m3, row.displacement_volume_m3, rel_tol=0, abs_tol=1e-9):
            return row
    lower = next(
        (left for left, right in zip(rows, rows[1:]) if left.displacement_volume_m3 < displacement_volume_m3 < right.displacement_volume_m3),
        None,
    )
    if lower is None:
        raise CalculationInputError("Could not bracket displacement in hydrostatic table")
    upper = rows[rows.index(lower) + 1]
    ratio = (
        (displacement_volume_m3 - lower.displacement_volume_m3)
        / (upper.displacement_volume_m3 - lower.displacement_volume_m3)
    )

    def lerp(a: float, b: float) -> float:
        return a + ratio * (b - a)

    return HydrostaticPoint(
        displacement_volume_m3=displacement_volume_m3,
        draft_extreme_m=lerp(lower.draft_extreme_m, upper.draft_extreme_m),
        lcf_from_ap_m=lerp(lower.lcf_from_ap_m, upper.lcf_from_ap_m),
        lcb_from_ap_m=lerp(lower.lcb_from_ap_m, upper.lcb_from_ap_m),
        transverse_metacentre_z_m=lerp(
            lower.transverse_metacentre_z_m, upper.transverse_metacentre_z_m
        ),
        mct_t_m_per_cm=lerp(lower.mct_t_m_per_cm, upper.mct_t_m_per_cm),
    )


def calculate_loading_condition(
    *,
    lightship: Lightship,
    items: Sequence[WeightItem],
    lbp_m: float,
    seawater_density_t_m3: float,
    hydrostatic_table: Sequence[HydrostaticPoint],
) -> dict[str, float]:
    """Calculate weight moments, drafts, trim, heel, GM and forward strength moment.

    Coordinate convention follows the course project: origin at AP on baseline;
    X positive forward, Y positive to port, Z positive upwards.
    """
    _finite_positive(lightship.mass_t, "lightship.mass_t")
    _finite_positive(lbp_m, "lbp_m")
    _finite_positive(seawater_density_t_m3, "seawater_density_t_m3")
    for name, value in (
        ("lightship.lcg_m", lightship.lcg_m),
        ("lightship.tcg_m", lightship.tcg_m),
        ("lightship.vcg_m", lightship.vcg_m),
        ("lightship.forward_moment_tm", lightship.forward_moment_tm),
    ):
        if not math.isfinite(value):
            raise CalculationInputError(f"{name} must be finite")

    displacement_t = lightship.mass_t
    moment_x_tm = lightship.mass_t * lightship.lcg_m
    moment_y_tm = lightship.mass_t * lightship.tcg_m
    moment_z_tm = lightship.mass_t * lightship.vcg_m
    free_surface_moment_tm = 0.0
    forward_moment_tm = lightship.forward_moment_tm

    for item in items:
        if not item.name.strip():
            raise CalculationInputError("Every weight item must have a name")
        if not math.isfinite(item.mass_t) or item.mass_t < 0:
            raise CalculationInputError(f"{item.name}: mass must be finite and non-negative")
        if not all(math.isfinite(value) for value in (
            item.lcg_m, item.tcg_m, item.vcg_m, item.free_surface_moment_tm
        )):
            raise CalculationInputError(f"{item.name}: coordinates and FSM must be finite")
        if item.free_surface_moment_tm < 0:
            raise CalculationInputError(f"{item.name}: FSM cannot be negative")
        displacement_t += item.mass_t
        moment_x_tm += item.mass_t * item.lcg_m
        moment_y_tm += item.mass_t * item.tcg_m
        moment_z_tm += item.mass_t * item.vcg_m
        free_surface_moment_tm += item.free_surface_moment_tm
        if item.include_in_forward_strength and item.lcg_m > lbp_m / 2:
            forward_moment_tm += item.mass_t * (item.lcg_m - lbp_m / 2)

    if displacement_t <= 0:
        raise CalculationInputError("Total displacement must be positive")

    lcg_m = moment_x_tm / displacement_t
    tcg_m = moment_y_tm / displacement_t
    vcg_m = moment_z_tm / displacement_t
    displacement_volume_m3 = displacement_t / seawater_density_t_m3
    hydro = interpolate_hydrostatics(displacement_volume_m3, hydrostatic_table)

    # Equations (3.2) and (3.3) / (5.2) and (5.3) in the course project.
    longitudinal_factor = (
        0.01 * (lcg_m - hydro.lcb_from_ap_m) * displacement_t
        / (lbp_m * hydro.mct_t_m_per_cm)
    )
    forward_draft_m = hydro.draft_extreme_m + (
        lbp_m / 2 - hydro.lcf_from_ap_m
    ) * longitudinal_factor
    aft_draft_m = hydro.draft_extreme_m - (
        lbp_m / 2 + hydro.lcf_from_ap_m
    ) * longitudinal_factor
    trim_m = forward_draft_m - aft_draft_m
    mean_draft_m = (forward_draft_m + aft_draft_m) / 2
    trim_angle_deg = 57.3 * trim_m / lbp_m

    free_surface_vcg_correction_m = free_surface_moment_tm / displacement_t
    corrected_vcg_m = vcg_m + free_surface_vcg_correction_m
    corrected_gm_m = hydro.transverse_metacentre_z_m - corrected_vcg_m
    if corrected_gm_m <= 0:
        raise CalculationInputError(
            "Corrected initial GM is non-positive; heel calculation is not meaningful"
        )
    heel_deg = 57.3 * tcg_m / corrected_gm_m

    return {
        "displacement_t": displacement_t,
        "displacement_volume_m3": displacement_volume_m3,
        "longitudinal_moment_tm": moment_x_tm,
        "transverse_moment_tm": moment_y_tm,
        "vertical_moment_tm": moment_z_tm,
        "lcg_m": lcg_m,
        "tcg_m": tcg_m,
        "vcg_m": vcg_m,
        "free_surface_moment_tm": free_surface_moment_tm,
        "free_surface_vcg_correction_m": free_surface_vcg_correction_m,
        "corrected_vcg_m": corrected_vcg_m,
        "draft_extreme_m": hydro.draft_extreme_m,
        "lcf_from_ap_m": hydro.lcf_from_ap_m,
        "lcb_from_ap_m": hydro.lcb_from_ap_m,
        "transverse_metacentre_z_m": hydro.transverse_metacentre_z_m,
        "mct_t_m_per_cm": hydro.mct_t_m_per_cm,
        "corrected_initial_gm_m": corrected_gm_m,
        "forward_draft_m": forward_draft_m,
        "aft_draft_m": aft_draft_m,
        "mean_draft_m": mean_draft_m,
        "trim_m": trim_m,
        "trim_angle_deg": trim_angle_deg,
        "heel_deg_port_positive": heel_deg,
        "forward_strength_moment_tm": forward_moment_tm,
    }
