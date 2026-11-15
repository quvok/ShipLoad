import pytest
from pydantic import ValidationError

from app.schemas.vessel import AxisDirection, VesselCreate, VesselType


def valid_vessel() -> dict:
    return {
        "name": "Example vessel",
        "vessel_type": VesselType.GENERAL_CARGO,
        "loa_m": 120.0,
        "lbp_m": 112.0,
        "moulded_breadth_m": 20.0,
        "moulded_depth_m": 10.0,
        "coordinate_convention": {
            "origin_description": "Approved vessel reference origin; see vessel booklet.",
            "x_axis_direction": AxisDirection.POSITIVE_FORWARD,
            "y_axis_direction": AxisDirection.POSITIVE_PORT,
            "z_axis_direction": AxisDirection.POSITIVE_UP,
            "vertical_datum_description": "Vertical datum as defined in approved vessel drawings.",
        },
    }


def test_vessel_schema_allows_missing_reference_convention_in_document_first_draft() -> None:
    data = valid_vessel()
    del data["coordinate_convention"]
    vessel = VesselCreate.model_validate(data)
    assert vessel.coordinate_convention is None


def test_vessel_schema_rejects_invalid_reference_convention_when_supplied() -> None:
    data = valid_vessel()
    data["coordinate_convention"] = {"origin_description": "AP"}
    with pytest.raises(ValidationError):
        VesselCreate.model_validate(data)


def test_vessel_schema_rejects_lbp_greater_than_loa() -> None:
    data = valid_vessel()
    data["lbp_m"] = 121.0
    with pytest.raises(ValidationError):
        VesselCreate.model_validate(data)


def test_vessel_schema_accepts_explicit_si_dimensions() -> None:
    vessel = VesselCreate.model_validate(valid_vessel())
    assert vessel.lbp_m == 112.0
    assert vessel.coordinate_convention.z_axis_direction == AxisDirection.POSITIVE_UP
