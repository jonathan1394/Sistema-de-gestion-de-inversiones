from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.app import create_app
from app.config import load_settings
from app.data.data_validator import INTERVAL_MS
from app.data.market_data import store_klines
from app.database.connection import get_connection
from app.prospecting.db import add_prospect, update_prospect_analysis


def _seed_candles(db_path: Path, symbol: str = "BTCUSDT") -> None:
    conn = get_connection(db_path)
    base_ms = 1_704_067_200_000
    for interval in ("1h", "4h", "1d"):
        step = INTERVAL_MS[interval]
        klines = []
        price = 100.0
        for idx in range(80):
            open_time = base_ms + idx * step
            open_price = price
            close_price = price + 1.0
            high_price = close_price + 0.5
            low_price = open_price - 0.5
            volume = 1_000 + idx
            klines.append(
                [
                    open_time,
                    str(open_price),
                    str(high_price),
                    str(low_price),
                    str(close_price),
                    str(volume),
                    open_time + step - 1,
                    str(volume * close_price),
                    10 + idx,
                    str(volume / 2),
                    str((volume * close_price) / 2),
                ]
            )
            price += 1.0
        store_klines(conn, symbol, interval, klines)

    add_prospect(conn, symbol, interval="1d", notes="seeded for evaluation")
    update_prospect_analysis(
        conn,
        symbol,
        "1d",
        score=0.81,
        trend="up",
        volatility="medium",
        volume_profile="normal",
        rsi_condition="neutral",
        signals_count=3,
        metadata={"source": "test"},
    )


def test_api_evaluation_endpoints(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "evaluation.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    load_settings.cache_clear()
    _seed_candles(db_path)

    with TestClient(create_app()) as client:
        health_resp = client.get("/api/v1/evaluation/data-health?symbols=BTCUSDT&intervals=1h,4h,1d")
        assert health_resp.status_code == 200
        health_data = health_resp.json()["data"]
        assert len(health_data) == 3
        assert all(row["count"] >= 50 for row in health_data)

        review_resp = client.get("/api/v1/evaluation/investment/BTCUSDT?interval=1d&backtest_interval=4h")
        assert review_resp.status_code == 200
        payload = review_resp.json()["data"]
        assert payload["symbol"] == "BTCUSDT"
        assert len(payload["data_health"]) >= 3
        assert payload["prospect"]["score"] == 0.81
        assert "checks" in payload["protocol"]

    load_settings.cache_clear()
