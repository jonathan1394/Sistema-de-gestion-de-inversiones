"""Shared helper functions for dashboard pages."""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

from app.data.market_data import get_candles

logger = logging.getLogger(__name__)


def candles_to_dataframe(candles: list) -> pd.DataFrame:
    """Convert a list of Candle objects into a DataFrame."""
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }
    )


def get_current_price(connection: sqlite3.Connection, symbol: str) -> Optional[float]:
    """Fetch the latest close price for symbol from candles (prefer 1h, then 4h, then 1d)."""
    for interval in ("1h", "4h", "1d"):
        candles = get_candles(
            connection=connection,
            symbol=symbol,
            interval=interval,
            limit=1,
            desc=True,
        )
        if candles and len(candles) > 0:
            return float(candles[0].close)
    return None


def get_portfolio_value(session_state: Any) -> float:
    """Return current portfolio value from cash plus marked-to-market positions."""
    cash = float(getattr(session_state, "portfolio_cash", 0.0))
    positions = getattr(session_state, "portfolio_positions", {})
    pos_value = 0.0
    for pos in positions.values():
        try:
            pos_value += float(pos.get("quantity", 0.0)) * float(pos.get("current_price", 0.0))
        except Exception:
            continue
    return cash + pos_value


def update_portfolio_prices(session_state: Any, prices: dict[str, float]) -> None:
    """Update session positions with latest prices and unrealized PnL."""
    positions = getattr(session_state, "portfolio_positions", {})
    for symbol, price in prices.items():
        if symbol not in positions:
            continue
        pos = positions[symbol]
        pos["current_price"] = price
        try:
            entry = float(pos.get("entry_price", 0.0))
            qty = float(pos.get("quantity", 0.0))
        except Exception:
            continue
        pos["unrealized_pnl"] = qty * (price - entry)
        pos["unrealized_pnl_pct"] = (price / entry - 1) * 100 if entry else 0.0


def add_snapshot(session_state: Any) -> None:
    """Store a timestamped portfolio snapshot with drawdown metrics."""
    tv = get_portfolio_value(session_state)
    peak = float(getattr(session_state, "portfolio_peak", tv))
    if tv > peak:
        peak = tv
    session_state.portfolio_peak = peak

    dd = (peak - tv) / peak * 100 if peak > 0 else 0.0
    snapshots = getattr(session_state, "portfolio_snapshots", [])
    snapshots.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_value": round(tv, 2),
        "cash": round(float(getattr(session_state, "portfolio_cash", 0.0)), 2),
        "drawdown_pct": round(dd, 2),
    })
    session_state.portfolio_snapshots = snapshots
