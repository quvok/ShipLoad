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
