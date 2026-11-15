from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "shipload-api"}


def test_status_does_not_claim_operational_readiness() -> None:
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json()["calculation_engine"] == "not_implemented"
    assert response.json()["operational_approval"] == "not_approved"


def test_loading_condition_validation_endpoint() -> None:
    response = client.post(
        "/api/v1/validation/loading-condition",
        json={
            "vessel_id": "vessel-1",
            "name": "Departure",
            "vessel_data_revision": "rev-1",
            "items": [{
                "item_id": "cargo-1",
                "description": "Palletised cargo",
                "kind": "cargo",
                "mass_kg": 12000,
                "position": {
                    "x_m": 12.5,
                    "y_m": 0,
                    "z_m": 3.2,
                    "position_source": "Cargo plan, frame reference verified",
                },
                "source_reference": "Cargo manifest, revision A",
            }],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REVIEW_REQUIRED"
    assert response.json()["item_count"] == 1
    assert "Расчёт водоизмещения" in response.json()["message"]


def test_loading_condition_validation_rejects_missing_liquid_tank() -> None:
    response = client.post(
        "/api/v1/validation/loading-condition",
        json={
            "vessel_id": "vessel-1",
            "name": "Departure",
            "vessel_data_revision": "rev-1",
            "items": [{
                "item_id": "ballast-1",
                "description": "Ballast water",
                "kind": "ballast",
                "mass_kg": 5000,
                "position": {
                    "x_m": 0,
                    "y_m": 0,
                    "z_m": 0,
                    "position_source": "Not applicable",
                },
                "source_reference": "Sounding record",
            }],
        },
    )
    assert response.status_code == 422
