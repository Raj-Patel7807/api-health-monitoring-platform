from fastapi.testclient import TestClient

from app.main import app


def test_health_reports_process_liveness() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-request-id"]


def test_secondary_delivery_routes_and_harness_are_unmounted() -> None:
    client = TestClient(app)
    assert client.get("/deliveries").status_code == 404
    assert client.post("/harness/email", json={}).status_code == 404
