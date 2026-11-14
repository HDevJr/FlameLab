from fastapi.testclient import TestClient

from backend.app.main import app


def test_f00_health():
    response = TestClient(app).get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "stage": "F00"}


def test_unimplemented_scientific_endpoints_are_not_falsely_exposed():
    response = TestClient(app).get("/api/experiments")
    assert response.status_code == 404
