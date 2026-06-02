"""Market decision utilities for timeframe analysis and confluence."""

from __future__ import annotations

import pandas as pd

from app.ai.market_summary import generate_market_summary
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.config import load_settings


def analyze_timeframe(conn, symbol: str, interval: str) -> dict | None:
    """Build summary metrics for one timeframe if data is sufficient."""
    candles = get_candles(
        connection=conn,
        symbol=symbol,
        interval=interval,
        limit=200,
        desc=True,
    )
    if not candles or len(candles) < 50:
        return None

    data = pd.DataFrame({
        "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
        "open": [c.open for c in candles],
        "high": [c.high for c in candles],
        "low": [c.low for c in candles],
        "close": [c.close for c in candles],
        "volume": [c.volume for c in candles],
    })

    try:
        summary = generate_market_summary(data, symbol=symbol, period=interval)
    except (ValueError, KeyError):
        return None

    return {
        "interval": interval,
        "price": summary.close_price,
        "return_pct": summary.return_pct,
        "trend": summary.condition.trend,
        "volatility": summary.condition.volatility,
        "rsi": summary.condition.rsi_condition,
        "volume": summary.condition.volume_profile,
        "summary_text": summary.condition.summary,
        "key_levels": summary.key_levels,
        "volatility_pct": summary.volatility_pct,
    }


def compute_confluence(results: list[dict]) -> int:
    """Return number of bullish trends across timeframe results."""
    TREND_ORDER = {"strong_up": 5, "up": 4, "sideways": 3, "down": 2, "strong_down": 1}
    bullish = 0
    for r in results:
        t = r.get("trend", "sideways")
        if TREND_ORDER.get(t, 3) >= 4:
            bullish += 1
    return bullish