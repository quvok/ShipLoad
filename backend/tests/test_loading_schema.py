import pytest
from pydantic import ValidationError

from app.schemas.loading import LoadingConditionCreate, LoadingItemCreate


def positional_item(item_id: str = "cargo-1") -> dict:
    return {
        "item_id": item_id,
        "description": "Palletised cargo",
        "kind": "cargo",
        "mass_kg": 12000,
        "position": {
            "x_m": 12.5, "y_m": 0, "z_m": 3.2,
            "position_source": "Cargo plan, frame reference verified",
        },
        "source_reference": "Cargo manifest, revision A",
    }


def test_loading_condition_accepts_explicit_position_and_mass() -> None:
    condition = LoadingConditionCreate(
        vessel_id="vessel-1",
        name="Departure",
        vessel_data_revision="rev-1",
        items=[positional_item()],
    )
    assert condition.items[0].mass_kg == 12000


def test_item_requires_exactly_one_location_reference() -> None:
    item = positional_item()
    item["tank_id"] = "T-01"
    with pytest.raises(ValidationError):
        LoadingItemCreate.model_validate(item)


def test_liquid_item_requires_tank_reference() -> None:
    item = positional_item()
    item["kind"] = "ballast"
    with pytest.raises(ValidationError):
        LoadingItemCreate.model_validate(item)


def test_mass_must_be_positive_and_finite() -> None:
    item = positional_item()
    item["mass_kg"] = 0
    with pytest.raises(ValidationError):
        LoadingItemCreate.model_validate(item)
    item["mass_kg"] = float("nan")
    with pytest.raises(ValidationError):
        LoadingItemCreate.model_validate(item)


def test_duplicate_item_ids_are_rejected() -> None:
    with pytest.raises(ValidationError):
        LoadingConditionCreate(
            vessel_id="vessel-1",
            name="Departure",
            vessel_data_revision="rev-1",
            items=[positional_item(), positional_item()],
        )
