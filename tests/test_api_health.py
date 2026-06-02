from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_app


def test_api_health_ok() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/api/v1/system/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "ok"
        assert payload["data"]["ok"] is True
