import pytest
from pydantic import ValidationError

from app.schemas.vessel_model import (
    CapacityPoint,
    CompartmentDefinition,
    CompartmentKind,
    SourceReference,
    VesselCalculationModel,
    assess_model_capabilities,
)


def source(page: int = 1) -> SourceReference:
    return SourceReference(
        document_id="doc-1",
        document_name="Vessel Booklet.pdf",
        page=page,
        location="Table 1",
    )


def test_bulk_carrier_model_uses_holds_and_capabilities_from_data():
    hold = CompartmentDefinition(
        code="HOLD_1",
        name="Cargo hold 1",
        kind=CompartmentKind.CARGO_HOLD,
        maximum_volume_m3=12000,
        capacity_curve=[
            CapacityPoint(
                filling_parameter=0,
                volume_m3=0,
                lcg_m=40,
                tcg_m=0,
                vcg_m=5,
                source=source(),
            ),
            CapacityPoint(
                filling_parameter=100,
                volume_m3=12000,
                lcg_m=40,
                tcg_m=0,
                vcg_m=5,
                source=source(),
            ),
        ],
        arrangement_source=source(),
        capacity_source=source(),
    )
    model = VesselCalculationModel(
        vessel_id="bulk-1",
        vessel_type="bulk_carrier",
        compartments=[hold],
    )
    report = assess_model_capabilities(model)
    assert report["compartment_kinds"] == ["cargo_hold"]
    assert report["capabilities"]["tank_or_hold_loading"] is True
    assert report["capabilities"]["large_angle_stability"] is False


def test_tanker_model_uses_tanks_without_bulk_carrier_defaults():
    tank = CompartmentDefinition(
        code="COT_1P",
        name="Cargo oil tank 1 port",
        kind=CompartmentKind.CARGO_TANK,
        maximum_volume_m3=8000,
        arrangement_source=source(),
    )
    model = VesselCalculationModel(
        vessel_id="tanker-1",
        vessel_type="tanker",
        compartments=[tank],
    )
    report = assess_model_capabilities(model)
    assert report["compartment_kinds"] == ["cargo_tank"]
    assert report["capabilities"]["tank_or_hold_loading"] is False
    assert "large_angle_stability" in report["missing"]


def test_capacity_curve_requires_source_and_increasing_fill_points():
    with pytest.raises(ValidationError, match="capacity curve requires its source"):
        CompartmentDefinition(
            code="H1",
            name="Hold",
            kind=CompartmentKind.CARGO_HOLD,
            capacity_curve=[
                CapacityPoint(
                    filling_parameter=0, volume_m3=0, lcg_m=1, tcg_m=0,
                    vcg_m=2, source=source(),
                )
            ],
            arrangement_source=source(),
        )


def test_model_rejects_duplicate_compartment_codes():
    space = CompartmentDefinition(
        code="H1",
        name="Hold 1",
        kind=CompartmentKind.CARGO_HOLD,
        arrangement_source=source(),
    )
    with pytest.raises(ValidationError, match="unique"):
        VesselCalculationModel(
            vessel_id="ship-1",
            vessel_type="bulk_carrier",
            compartments=[space, space],
        )


def test_model_does_not_infer_capabilities_from_vessel_type():
    model = VesselCalculationModel(vessel_id="b1", vessel_type="bulk_carrier")
    report = assess_model_capabilities(model)
    assert report["available"] == []
    assert len(report["missing"]) == 6
