import pytest
from pydantic import ValidationError

from app.schemas.tank import TankCreate


def test_tank_without_capacity_can_be_registered_from_arrangement_plan():
    tank = TankCreate(
        tank_code="WB-1P",
        name="Форпиковый балластный танк",
        tank_type="ballast",
        arrangement_source_reference="План расположения танков, лист 3",
    )
    assert tank.nominal_capacity_m3 is None


def test_nominal_capacity_requires_document_source():
    with pytest.raises(ValidationError):
        TankCreate(
            tank_code="FO-1",
            name="Танк топлива",
            tank_type="fuel_oil",
            nominal_capacity_m3=120.5,
            arrangement_source_reference="План расположения танков, лист 4",
        )


def test_capacity_must_be_positive_and_finite():
    with pytest.raises(ValidationError):
        TankCreate(
            tank_code="FW-1",
            name="Танк пресной воды",
            tank_type="fresh_water",
            nominal_capacity_m3=0,
            capacity_source_reference="Таблица вместимости, лист 2",
            arrangement_source_reference="План расположения танков, лист 4",
        )
