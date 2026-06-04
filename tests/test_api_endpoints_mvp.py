from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.app import create_app


def test_api_config_exists() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/api/v1/config")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "ok"
        assert payload["data"]["mode"]
        assert payload["data"]["kill_switch"] in {True, False}
        assert "database" in payload["data"]
        assert "binance_api_key" not in payload["data"]


def test_api_alert_rules_roundtrip(tmp_path, monkeypatch) -> None:
    rules_file = tmp_path / "alert_rules.json"
    monkeypatch.setattr("app.api.routes.alerts.RULES_FILE", rules_file)

    payload = {"price": {"enabled": False, "check_interval_seconds": 900}}

    with TestClient(create_app()) as client:
        post_resp = client.post("/api/v1/alerts/rules", json=payload)
        assert post_resp.status_code == 200
        assert post_resp.json()["data"]["updated"] is True

        get_resp = client.get("/api/v1/alerts/rules")
        assert get_resp.status_code == 200
        assert get_resp.json()["data"] == payload


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
