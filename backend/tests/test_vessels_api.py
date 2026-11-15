from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import app
from app.models import Base

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def override_session():
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_session] = override_session
client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def vessel_payload():
    return {
        "name": "Тестовое судно",
        "vessel_type": "general_cargo",
        "loa_m": 120,
        "lbp_m": 110,
        "moulded_breadth_m": 20,
        "moulded_depth_m": 10,
        "coordinate_convention": {
            "origin_description": "Пересечение основной плоскости и мидель-шпангоута",
            "x_axis_direction": "positive_forward",
            "y_axis_direction": "positive_starboard",
            "z_axis_direction": "positive_up",
            "vertical_datum_description": "Основная плоскость судна",
        },
    }


def test_create_and_list_vessels():
    response = client.post("/api/v1/vessels", json=vessel_payload())
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "Тестовое судно"
    assert created["data_status"] == "DRAFT"
    assert created["id"]

    listed = client.get("/api/v1/vessels")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == created["id"]


def test_get_vessel_by_id():
    created = client.post("/api/v1/vessels", json=vessel_payload()).json()
    response = client.get(f"/api/v1/vessels/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_missing_vessel_returns_404():
    response = client.get("/api/v1/vessels/not-a-vessel")
    assert response.status_code == 404


def tank_payload():
    return {
        "tank_code": "WB-1P",
        "name": "Левый балластный танк № 1",
        "tank_type": "ballast",
        "nominal_capacity_m3": 850.0,
        "arrangement_source_reference": "План расположения танков, лист 3",
        "capacity_source_reference": "Таблица вместимости танков, лист 12",
    }


def test_create_and_list_tanks():
    vessel_id = client.post("/api/v1/vessels", json=vessel_payload()).json()["id"]
    created = client.post(
        f"/api/v1/vessels/{vessel_id}/tanks",
        json=tank_payload(),
    )
    assert created.status_code == 201
    assert created.json()["tank_code"] == "WB-1P"
    assert created.json()["data_status"] == "REVIEW_REQUIRED"
    assert created.json()["nominal_capacity_m3"] == 850.0

    listed = client.get(f"/api/v1/vessels/{vessel_id}/tanks")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_tank_code_must_be_unique_per_vessel():
    vessel_id = client.post("/api/v1/vessels", json=vessel_payload()).json()["id"]
    url = f"/api/v1/vessels/{vessel_id}/tanks"
    assert client.post(url, json=tank_payload()).status_code == 201
    assert client.post(url, json=tank_payload()).status_code == 409


def test_loading_condition_requires_tank_from_same_vessel():
    vessel_id = client.post("/api/v1/vessels", json=vessel_payload()).json()["id"]
    payload = loading_condition_payload(vessel_id)
    payload["items"] = [{
        "item_id": "ballast-001",
        "description": "Балласт в танке WB-1P",
        "kind": "ballast",
        "mass_kg": 500000,
        "tank_id": "missing-tank-id",
        "source_reference": "Ведомость замеров танков, запись 1",
    }]
    response = client.post("/api/v1/loading-conditions", json=payload)
    assert response.status_code == 422


def test_liquid_item_must_match_registered_tank_type():
    vessel_id = client.post("/api/v1/vessels", json=vessel_payload()).json()["id"]
    tank = tank_payload()
    tank["tank_type"] = "fuel_oil"
    tank["nominal_capacity_m3"] = 400
    tank["capacity_source_reference"] = "Таблица вместимости, лист 8"
    tank_id = client.post(
        f"/api/v1/vessels/{vessel_id}/tanks",
        json=tank,
    ).json()["id"]
    payload = loading_condition_payload(vessel_id)
    payload["items"] = [{
        "item_id": "ballast-001",
        "description": "Балластная нагрузка",
        "kind": "ballast",
        "mass_kg": 500000,
        "tank_id": tank_id,
        "source_reference": "Ведомость замеров танков, запись 1",
    }]
    response = client.post("/api/v1/loading-conditions", json=payload)
    assert response.status_code == 422


def loading_condition_payload(vessel_id):
    return {
        "vessel_id": vessel_id,
        "name": "Тестовое загрузочное условие",
        "vessel_data_revision": "DRAFT-REV-001",
        "notes": "Только проверка сохранения исходных данных.",
        "items": [
            {
                "item_id": "cargo-001",
                "description": "Тестовая партия груза",
                "kind": "cargo",
                "mass_kg": 12500,
                "position": {
                    "x_m": 15.0,
                    "y_m": 0.0,
                    "z_m": 2.5,
                    "position_source": "Тестовая ссылка на план размещения",
                },
                "source_reference": "Тестовый грузовой план, лист 1",
            }
        ],
    }


def test_create_and_retrieve_loading_condition():
    vessel_response = client.post("/api/v1/vessels", json=vessel_payload())
    assert vessel_response.status_code == 201
    vessel_id = vessel_response.json()["id"]

    created_response = client.post(
        "/api/v1/loading-conditions",
        json=loading_condition_payload(vessel_id),
    )
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["status"] == "REVIEW_REQUIRED"
    assert created["item_count"] == 1
    assert "Расчёт водоизмещения" in created["message"]

    listed = client.get(f"/api/v1/vessels/{vessel_id}/loading-conditions")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == created["id"]

    detail = client.get(f"/api/v1/loading-conditions/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["items"][0]["mass_kg"] == 12500
    assert detail.json()["items"][0]["source_reference"] == "Тестовый грузовой план, лист 1"


def test_create_loading_condition_persists_multiple_items():
    vessel_id = client.post("/api/v1/vessels", json=vessel_payload()).json()["id"]
    payload = loading_condition_payload(vessel_id)
    second = dict(payload["items"][0])
    second["item_id"] = "stores-001"
    second["description"] = "Судовые запасы"
    second["mass_kg"] = 850
    second["position"] = {
        "x_m": -8.0,
        "y_m": 1.2,
        "z_m": 4.0,
        "position_source": "Складская ведомость и план размещения",
    }
    second["source_reference"] = "Ведомость судовых запасов, лист 2"
    payload["items"].append(second)

    response = client.post("/api/v1/loading-conditions", json=payload)
    assert response.status_code == 201
    assert response.json()["item_count"] == 2

    detail = client.get(f"/api/v1/loading-conditions/{response.json()['id']}")
    assert detail.status_code == 200
    assert {item["item_id"] for item in detail.json()["items"]} == {
        "cargo-001", "stores-001"
    }


def test_create_loading_condition_rejects_unknown_vessel():
    response = client.post(
        "/api/v1/loading-conditions",
        json=loading_condition_payload("missing-vessel"),
    )
    assert response.status_code == 404


def test_get_missing_loading_condition_returns_404():
    response = client.get("/api/v1/loading-conditions/missing-condition")
    assert response.status_code == 404
