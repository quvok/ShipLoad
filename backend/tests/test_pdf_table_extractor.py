from app.services.pdf_table_extractor import _classify_table


def test_seasonal_freeboard_draft_displacement_table_is_loading_condition():
    sample = "Seasonal Freeboard Draft (Ext.) Displacement (tonnes) Deadweight (tonnes)"
    assert _classify_table(sample) == "loading_condition"


def test_hydrostatic_table_uses_distinctive_hydrostatic_columns():
    sample = "Draft Displacement L.C.F FROM AP L.C.B FROM AP TPC MCT KM"
    assert _classify_table(sample) == "hydrostatics"


def test_tank_capacity_table_is_not_misclassified_as_hydrostatics():
    sample = "NO.1 CARGO TANK Sounding Ullage Capacity m3"
    assert _classify_table(sample) == "tank_capacity"


def test_longitudinal_strength_table_uses_strength_headers():
    sample = "Frame No. Bending Moments (ton-m) Shear Force (ton) Hogging Sagging"
    assert _classify_table(sample) == "strength"


def test_stability_curve_table_uses_righting_arm_headers():
    sample = "Heel Angle GZ Curve Righting Lever KN"
    assert _classify_table(sample) == "stability"

def test_deadweight_scale_with_tpc_and_mct_is_loading_condition():
    sample = "DEADWEIGHT SCALE T.P.C M.T.C DRAFT DISPL. DEADWEIGHT"
    assert _classify_table(sample) == "loading_condition"


def test_free_surface_table_is_separated_from_generic_tank_capacity():
    sample = "TANK NAME NO.1 CARGO TANK F.S.M T-M"
    assert _classify_table(sample) == "free_surface"


def test_draft_correction_table_has_a_specific_kind():
    sample = "Trim by the Stern Correction Values Aft Mark1 Mid Mark Fore Mark"
    assert _classify_table(sample) == "draft_corrections"


def test_windage_heeling_moment_table_has_a_specific_kind():
    sample = "Lateral Area & Heeling Moment due to Wind Pressure draft trim heel"
    assert _classify_table(sample) == "windage"


def test_ice_mass_table_has_a_specific_kind():
    sample = "Mass of ice per square meter of the windage area LCG VCG"
    assert _classify_table(sample) == "ice_loading"


def test_inclining_experiment_table_has_a_specific_kind():
    sample = "Inclining Experiment DISP Slope of Tangent GoM"
    assert _classify_table(sample) == "inclining_experiment"


def test_propeller_immersion_table_has_a_specific_kind():
    sample = "Propeller Immersion Table dAp = Da - A x trim / LBP"
    assert _classify_table(sample) == "propeller_immersion"


def test_trimming_table_has_a_specific_kind():
    sample = "Trimming Table new drafts due to adding weight in cargo tank"
    assert _classify_table(sample) == "trimming_table"
