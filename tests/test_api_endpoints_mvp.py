from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_app


def test_api_config_exists() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/api/v1/config")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "ok"
        assert "database" in payload["data"]


def test_api_backtest_strategies() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/api/v1/backtest/strategies")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        assert any(x["id"] == "ma" for x in data)
