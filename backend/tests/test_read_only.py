"""Demonstração pública somente leitura (FLAMELAB_READ_ONLY)."""

import io

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("FLAMELAB_READ_ONLY", "true")
    return TestClient(app)


def test_writes_are_blocked_with_explicit_error(client):
    r = client.post("/api/imports", files={"file": ("a.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")})
    assert r.status_code == 403 and r.json()["error"]["code"] == "READ_ONLY_DEMO"
    assert client.post("/api/records/X/review", json={}).status_code == 403
    assert client.post("/api/simulations", json={"scenario_id": "S"}).status_code == 403
    assert client.delete("/api/anything").status_code == 403


def test_reads_and_ask_still_work(client):
    assert client.get("/api/health").status_code == 200
    st = client.get("/api/status").json()["data"]
    assert st["read_only"] is True
    r = client.post("/api/ask", json={"question": "Qual era a pressão no ensaio M1?"})
    assert r.status_code == 200 and "data" in r.json()


def test_status_reports_not_read_only_by_default(monkeypatch):
    monkeypatch.delenv("FLAMELAB_READ_ONLY", raising=False)
    assert TestClient(app).get("/api/status").json()["data"]["read_only"] is False
