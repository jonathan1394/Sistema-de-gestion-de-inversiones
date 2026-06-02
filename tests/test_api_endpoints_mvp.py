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


def test_api_risk_evaluate_contract() -> None:
    payload = {
        "symbol": "BTCUSDT",
        "direction": "BUY",
        "entry_price": 100.0,
        "capital": 1000.0,
        "confidence": 0.5,
        "portfolio": {
            "total_capital": 1000.0,
            "cash": 1000.0,
            "positions": {},
            "asset_classes": {},
        },
    }

    with TestClient(create_app()) as client:
        resp = client.post("/api/v1/risk/evaluate", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "approved" in body["data"]
    assert "rejection_reason" in body["data"]
