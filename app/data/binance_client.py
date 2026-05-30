from __future__ import annotations

import time
from typing import Any

import requests

from app.config import BinanceConfig


class BinanceClient:
    def __init__(self, config: BinanceConfig) -> None:
        self._config = config

    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
        limit: int = 1000,
    ) -> list[list[Any]]:
        params: dict[str, Any] = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        }
        if start_time_ms is not None:
            params["startTime"] = start_time_ms
        if end_time_ms is not None:
            params["endTime"] = end_time_ms

        endpoint = f"{self._config.base_url}/api/v3/klines"
        retries = 0

        while True:
            try:
                response = requests.get(
                    endpoint,
                    params=params,
                    timeout=self._config.request_timeout_seconds,
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                retries += 1
                if retries > self._config.max_retries:
                    raise RuntimeError(
                        f"Binance request failed after {self._config.max_retries} retries"
                    ) from exc
                time.sleep(self._config.retry_delay_seconds)
