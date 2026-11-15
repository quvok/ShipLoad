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
