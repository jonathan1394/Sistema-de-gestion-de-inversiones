"""Tests for app/data/binance_client.py."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
import requests

from app.config import BinanceConfig
from app.data.binance_client import BinanceClient


def _client() -> BinanceClient:
    return BinanceClient(
        BinanceConfig(
            base_url="https://api.binance.test",
            request_timeout_seconds=5,
            max_retries=1,
            retry_delay_seconds=0,
        )
    )


def test_get_klines_calls_expected_endpoint(monkeypatch):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = [[1, "100", "110"]]
    mock_get = Mock(return_value=response)
    monkeypatch.setattr("app.data.binance_client.requests.get", mock_get)

    data = _client().get_klines("btcusdt", "1h", start_time_ms=10, end_time_ms=20, limit=5)

    assert data == [[1, "100", "110"]]
    mock_get.assert_called_once_with(
        "https://api.binance.test/api/v3/klines",
        params={"symbol": "BTCUSDT", "interval": "1h", "limit": 5, "startTime": 10, "endTime": 20},
        timeout=5,
    )


def test_get_klines_retries_and_raises(monkeypatch):
    mock_get = Mock(side_effect=requests.RequestException("network down"))
    monkeypatch.setattr("app.data.binance_client.requests.get", mock_get)

    with pytest.raises(RuntimeError, match="Binance request failed"):
        _client().get_klines("BTCUSDT", "1h")

    assert mock_get.call_count == 2
