"""Deterministic loading-condition and hydrostatic calculations.

The equations implemented here reproduce the method written in the user's
course project, sections 2–5. They are not a substitute for the approved
stability booklet, class criteria, or an approved ship loading instrument.
"""
from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass


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
    forward_moment_tm: float | None = None


@dataclass(frozen=True)
class HydrostaticPoint:
    """One approved hydrostatic-table row; Xf and Xc are measured from AP."""

    displacement_volume_m3: float
    draft_extreme_m: float
    lcf_from_ap_m: float
    lcb_from_ap_m: float
    transverse_metacentre_z_m: float
    mct_t_m_per_cm: float


@dataclass(frozen=True)
class KNPoint:
    heel_angle_deg: float
    kn_m: float


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
    for index, row in enumerate(rows):
        _finite_positive(row.displacement_volume_m3, "hydrostatic displacement volume")
        _finite_positive(row.mct_t_m_per_cm, "MCT")
        if not all(math.isfinite(value) for value in (
            row.draft_extreme_m,
            row.lcf_from_ap_m,
            row.lcb_from_ap_m,
            row.transverse_metacentre_z_m,
        )):
            raise CalculationInputError("Hydrostatic table contains a non-finite value")
        if index and row.displacement_volume_m3 <= rows[index - 1].displacement_volume_m3:
            raise CalculationInputError("Hydrostatic displacement rows must be strictly increasing")
    if displacement_volume_m3 < rows[0].displacement_volume_m3 or displacement_volume_m3 > rows[-1].displacement_volume_m3:
        raise CalculationInputError("Displacement is outside hydrostatic table; extrapolation is prohibited")
    for row in rows:
        if math.isclose(displacement_volume_m3, row.displacement_volume_m3, rel_tol=0, abs_tol=1e-9):
            return row
    lower_index = next(
        (index for index in range(len(rows) - 1)
         if rows[index].displacement_volume_m3 < displacement_volume_m3
         < rows[index + 1].displacement_volume_m3),
        None,
    )
    if lower_index is None:
        raise CalculationInputError("Could not bracket displacement in hydrostatic table")
    lower = rows[lower_index]
    upper = rows[lower_index + 1]
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
) -> dict[str, float | None]:
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
    ):
        if not math.isfinite(value):
            raise CalculationInputError(f"{name} must be finite")
    if lightship.forward_moment_tm is not None and not math.isfinite(lightship.forward_moment_tm):
        raise CalculationInputError("lightship.forward_moment_tm must be finite")

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
        if forward_moment_tm is not None and item.include_in_forward_strength and item.lcg_m > lbp_m / 2:
            forward_moment_tm += item.mass_t * (item.lcg_m - lbp_m / 2)
        aggregate_values = (
            displacement_t, moment_x_tm, moment_y_tm, moment_z_tm,
            free_surface_moment_tm,
        )
        if not all(math.isfinite(value) for value in aggregate_values) or (
            forward_moment_tm is not None and not math.isfinite(forward_moment_tm)
        ):
            raise CalculationInputError("Aggregate loading moments exceed the supported numeric range")

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


def calculate_gz_curve(
    *,
    kn_curve: Sequence[KNPoint],
    corrected_vcg_m: float,
) -> dict[str, object]:
    """Convert a source KN curve to GZ and integrate the tabulated righting arms."""
    if not math.isfinite(corrected_vcg_m):
        raise CalculationInputError("corrected_vcg_m must be finite")
    if len(kn_curve) < 2:
        raise CalculationInputError("At least two KN curve points are required")
    points = sorted(kn_curve, key=lambda point: point.heel_angle_deg)
    if points[0].heel_angle_deg != 0 or not math.isclose(points[0].kn_m, 0, abs_tol=1e-6):
        raise CalculationInputError("KN curve must start at heel angle 0 with KN=0")
    for index, point in enumerate(points):
        if not math.isfinite(point.heel_angle_deg) or not 0 <= point.heel_angle_deg <= 180:
            raise CalculationInputError("KN heel angles must be finite and between 0 and 180 degrees")
        if not math.isfinite(point.kn_m):
            raise CalculationInputError("KN curve contains a non-finite arm")
        if index and point.heel_angle_deg <= points[index - 1].heel_angle_deg:
            raise CalculationInputError("KN curve heel angles must be strictly increasing")

    curve: list[dict[str, float]] = []
    accumulated = 0.0
    previous_angle = 0.0
    previous_gz = 0.0
    for point in points:
        radians = math.radians(point.heel_angle_deg)
        gz = point.kn_m - corrected_vcg_m * math.sin(radians)
        if not math.isfinite(gz):
            raise CalculationInputError("Calculated GZ exceeds the supported numeric range")
        if curve:
            accumulated += (previous_gz + gz) * 0.5 * math.radians(
                point.heel_angle_deg - previous_angle
            )
        curve.append({
            "heel_angle_deg": point.heel_angle_deg,
            "kn_m": point.kn_m,
            "gz_m": gz,
            "dynamic_arm_m_rad": accumulated,
        })
        previous_angle = point.heel_angle_deg
        previous_gz = gz

    def arm_at(angle: float) -> float | None:
        if angle > points[-1].heel_angle_deg:
            return None
        for index, point in enumerate(points):
            if math.isclose(point.heel_angle_deg, angle, rel_tol=0, abs_tol=1e-9):
                return curve[index]["gz_m"]
            if index and points[index - 1].heel_angle_deg < angle < point.heel_angle_deg:
                left = points[index - 1]
                right = point
                fraction = (angle - left.heel_angle_deg) / (
                    right.heel_angle_deg - left.heel_angle_deg
                )
                return curve[index - 1]["gz_m"] + fraction * (
                    curve[index]["gz_m"] - curve[index - 1]["gz_m"]
                )
        return None

    def area_to(angle: float) -> float | None:
        terminal_arm = arm_at(angle)
        if terminal_arm is None:
            return None
        included = [(0.0, 0.0)]
        included.extend(
            (row["heel_angle_deg"], row["gz_m"])
            for row in curve if 0 < row["heel_angle_deg"] < angle
        )
        included.append((angle, terminal_arm))
        return sum(
            (left_y + right_y) * 0.5 * math.radians(right_x - left_x)
            for (left_x, left_y), (right_x, right_y) in itertools.pairwise(included)
        )

    maximum = max(curve, key=lambda row: row["gz_m"])
    return {
        "method": "GZ = KN - corrected_VCG * sin(heel); trapezoidal integration in radians",
        "points": curve,
        "maximum_gz_m": maximum["gz_m"],
        "heel_angle_at_maximum_deg": maximum["heel_angle_deg"],
        "area_to_30_deg_m_rad": area_to(30),
        "area_to_40_deg_m_rad": area_to(40),
        "area_30_to_40_deg_m_rad": (
            area_to(40) - area_to(30)
            if area_to(30) is not None and area_to(40) is not None else None
        ),
        "status": "ESTIMATE_ONLY",
        "note": "Критерии IMO/Class и угол заливания автоматически не оцениваются этим модулем.",
    }
