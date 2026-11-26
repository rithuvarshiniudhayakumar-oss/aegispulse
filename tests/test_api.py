import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AEGISPULSE_DB", str(tmp_path / "api.db"))
    from apps.api.main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_simulate_creates_then_deduplicates(client):
    first = client.post("/simulate", json={"scenario": "Database Overload", "seed": 1}).json()
    assert first["root_cause"] == "Database"
    assert first["incident_id"] and not first["deduplicated"]
    second = client.post("/simulate", json={"scenario": "Database Overload", "seed": 2}).json()
    assert second["deduplicated"] and second["incident_id"] == first["incident_id"]


def test_incident_lifecycle(client):
    iid = client.post("/simulate", json={"scenario": "Payment Service Failure", "seed": 1}).json()["incident_id"]
    assert client.patch(f"/incidents/{iid}/status", json={"status": "ACKNOWLEDGED"}).status_code == 200
    assert client.patch(f"/incidents/{iid}/status", json={"status": "RESOLVED"}).status_code == 200
    assert client.patch(f"/incidents/{iid}/status", json={"status": "ACKNOWLEDGED"}).status_code == 409


def test_unknown_scenario_rejected(client):
    assert client.post("/simulate", json={"scenario": "Nope"}).status_code == 422


def test_prometheus_metrics(client):
    client.post("/simulate", json={"scenario": "Normal Operations", "seed": 3})
    assert "aegispulse_cycles_total" in client.get("/metrics").text
