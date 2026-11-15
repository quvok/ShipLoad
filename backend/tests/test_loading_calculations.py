import pytest

from app.services.loading_calculations import (
    CalculationInputError,
    HydrostaticPoint,
    KNPoint,
    Lightship,
    WeightItem,
    calculate_gz_curve,
    calculate_loading_condition,
    interpolate_hydrostatics,
)


def test_course_project_optimal_condition_reference_case():
    # Reference values transcribed from KP_TUS_Gr1_P18_3.docx, pp. 15–19.
    # The inputs are the published aggregate values, not operational ship data.
    lightship = Lightship(
        mass_t=47087.2,
        lcg_m=119.245,
        tcg_m=-0.106,
        vcg_m=16.538,
        forward_moment_tm=1_386_360.0,
    )
    deadweight_mass = 90717.2
    displacement = 137804.4
    lcg = 141.19
    tcg = 0.04
    vcg = 16.69
    fsm = 141922.4
    # Aggregate item preserves the documented totals. Its forward strength
    # moment is independently represented by the course project's +Mx value.
    item = WeightItem(
        name="Aggregated deadweight",
        mass_t=deadweight_mass,
        lcg_m=(displacement * lcg - lightship.mass_t * lightship.lcg_m) / deadweight_mass,
        tcg_m=(displacement * tcg - lightship.mass_t * lightship.tcg_m) / deadweight_mass,
        vcg_m=(displacement * vcg - lightship.mass_t * lightship.vcg_m) / deadweight_mass,
        free_surface_moment_tm=fsm,
        include_in_forward_strength=False,
    )
    table = [
        HydrostaticPoint(
            displacement_volume_m3=135000.0,
            draft_extreme_m=12.65,
            lcf_from_ap_m=129.60,
            lcb_from_ap_m=141.30,
            transverse_metacentre_z_m=25.45,
            mct_t_m_per_cm=2780.0,
        ),
        HydrostaticPoint(
            displacement_volume_m3=135367.8,
            draft_extreme_m=12.68,
            lcf_from_ap_m=129.53,
            lcb_from_ap_m=141.35,
            transverse_metacentre_z_m=25.42,
            mct_t_m_per_cm=2788.9,
        ),
        HydrostaticPoint(
            displacement_volume_m3=136000.0,
            draft_extreme_m=12.75,
            lcf_from_ap_m=129.40,
            lcb_from_ap_m=141.40,
            transverse_metacentre_z_m=25.35,
            mct_t_m_per_cm=2800.0,
        ),
    ]

    result = calculate_loading_condition(
        lightship=lightship,
        items=[item],
        lbp_m=283.1,
        seawater_density_t_m3=1.018,
        hydrostatic_table=table,
    )

    assert result["displacement_t"] == pytest.approx(137804.4, abs=0.01)
    assert result["displacement_volume_m3"] == pytest.approx(135367.8, abs=0.1)
    assert result["lcg_m"] == pytest.approx(141.19, abs=0.01)
    assert result["tcg_m"] == pytest.approx(0.04, abs=0.01)
    assert result["corrected_vcg_m"] == pytest.approx(17.72, abs=0.02)
    assert result["corrected_initial_gm_m"] == pytest.approx(7.70, abs=0.02)
    assert result["forward_draft_m"] == pytest.approx(12.68, abs=0.02)
    assert result["aft_draft_m"] == pytest.approx(12.76, abs=0.02)
    assert result["mean_draft_m"] == pytest.approx(12.72, abs=0.02)
    assert result["trim_m"] == pytest.approx(-0.08, abs=0.02)
    assert result["heel_deg_port_positive"] == pytest.approx(0.30, abs=0.02)
    assert result["forward_strength_moment_tm"] == pytest.approx(1_386_360.0)


def test_hydrostatic_interpolation_is_linear_between_rows():
    table = [
        HydrostaticPoint(100.0, 10.0, 40.0, 50.0, 20.0, 1000.0),
        HydrostaticPoint(200.0, 12.0, 42.0, 52.0, 22.0, 1200.0),
    ]
    result = interpolate_hydrostatics(150.0, table)
    assert result.draft_extreme_m == pytest.approx(11.0)
    assert result.lcf_from_ap_m == pytest.approx(41.0)
    assert result.lcb_from_ap_m == pytest.approx(51.0)
    assert result.transverse_metacentre_z_m == pytest.approx(21.0)
    assert result.mct_t_m_per_cm == pytest.approx(1100.0)


def test_hydrostatic_interpolation_rejects_extrapolation():
    table = [
        HydrostaticPoint(100.0, 10.0, 40.0, 50.0, 20.0, 1000.0),
        HydrostaticPoint(200.0, 12.0, 42.0, 52.0, 22.0, 1200.0),
    ]
    with pytest.raises(CalculationInputError, match="extrapolation is prohibited"):
        interpolate_hydrostatics(250.0, table)


def test_non_positive_corrected_gm_is_rejected():
    lightship = Lightship(1000.0, 50.0, 0.0, 20.0, 0.0)
    hydro = [
        HydrostaticPoint(1000.0, 5.0, 40.0, 50.0, 15.0, 100.0),
        HydrostaticPoint(2000.0, 6.0, 40.0, 50.0, 15.0, 100.0),
    ]
    with pytest.raises(CalculationInputError, match="non-positive"):
        calculate_loading_condition(
            lightship=lightship,
            items=[],
            lbp_m=100.0,
            seawater_density_t_m3=1.0,
            hydrostatic_table=hydro,
        )


def test_forward_longitudinal_moment_adds_only_loads_forward_of_midship():
    lightship = Lightship(1000.0, 50.0, 0.0, 10.0, 1_386_360.0)
    hydro = [
        HydrostaticPoint(1000.0, 5.0, 40.0, 50.0, 20.0, 100.0),
        HydrostaticPoint(1200.0, 6.0, 40.0, 50.0, 20.0, 100.0),
    ]
    result = calculate_loading_condition(
        lightship=lightship,
        items=[
            WeightItem("Forward load", 100.0, 200.0, 0.0, 5.0),
            WeightItem("Aft load", 50.0, 20.0, 0.0, 5.0),
        ],
        lbp_m=100.0,
        seawater_density_t_m3=1.0,
        hydrostatic_table=hydro,
    )
    assert result["forward_strength_moment_tm"] == pytest.approx(
        1_386_360.0 + 100.0 * (200.0 - 50.0)
    )


def test_kn_curve_calculates_gz_and_dynamic_stability_without_extrapolation():
    curve = calculate_gz_curve(
        kn_curve=[KNPoint(0, 0), KNPoint(10, 4.429), KNPoint(20, 8.785),
                  KNPoint(30, 13.061), KNPoint(40, 15.975)],
        corrected_vcg_m=17.72,
    )
    assert curve["points"][3]["gz_m"] == pytest.approx(4.201, abs=0.01)
    assert curve["area_to_30_deg_m_rad"] == pytest.approx(1.07, abs=0.03)
    assert curve["area_to_40_deg_m_rad"] is not None

    limited = calculate_gz_curve(
        kn_curve=[KNPoint(0, 0), KNPoint(20, 8.785)],
        corrected_vcg_m=17.72,
    )
    assert limited["area_to_30_deg_m_rad"] is None


def test_course_project_optimal_plan_with_source_hydrostatic_bracket():
    lightship = Lightship(47087.2, 119.245, -0.106, 16.538)
    items = [
        WeightItem("Cargo", 84190, 154.03, 0, 16.77, 103989.5),
        WeightItem("Fresh water", 279.8, 17.16, 5.83, 23.32, 778.6),
        WeightItem("Diesel", 220, 49.99, 20.36, 16.32, 278.3),
        WeightItem("Oil", 395.4, 24.23, -0.54, 19.62, 248.6),
        WeightItem("Heavy fuel", 4086, 202.93, -0.09, 16.05, 22669.7),
        WeightItem("Waste", 247, 31.59, 20.01, 12.90, 231.8),
        WeightItem("Other weights", 199, 110.02, 0, 28.38, 20),
        WeightItem("Aft peak ballast", 1100, -9.20, 0, 16.09, 13705.9),
    ]
    hydro = [
        HydrostaticPoint(134919, 12.65, 129.61, 141.39, 25.44, 2780.6),
        HydrostaticPoint(135573, 12.70, 129.49, 141.33, 25.41, 2792.7),
    ]
    result = calculate_loading_condition(
        lightship=lightship,
        items=items,
        lbp_m=283.1,
        seawater_density_t_m3=1.018,
        hydrostatic_table=hydro,
    )

    assert result["displacement_t"] == pytest.approx(137804.4)
    assert result["lcg_m"] == pytest.approx(141.19, abs=0.02)
    assert result["tcg_m"] == pytest.approx(0.04, abs=0.02)
    assert result["corrected_vcg_m"] == pytest.approx(17.72, abs=0.02)
    assert result["corrected_initial_gm_m"] == pytest.approx(7.70, abs=0.03)
    assert result["forward_draft_m"] == pytest.approx(12.68, abs=0.02)
    assert result["aft_draft_m"] == pytest.approx(12.76, abs=0.02)
    assert result["mean_draft_m"] == pytest.approx(12.72, abs=0.02)
    assert result["trim_m"] == pytest.approx(-0.08, abs=0.02)
    assert result["heel_deg_port_positive"] == pytest.approx(0.30, abs=0.02)
