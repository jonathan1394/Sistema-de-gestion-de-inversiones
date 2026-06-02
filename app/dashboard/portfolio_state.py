"""Shared portfolio state helpers for Streamlit dashboard.

Do not import `app.dashboard.main` from page modules: `main` calls `st.set_page_config`
at import time and Streamlit requires that to be the first Streamlit command.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st


def get_portfolio_value() -> float:
    """Return current portfolio value from cash plus marked-to-market positions."""

    cash = float(st.session_state.get("portfolio_cash", 0.0))
    positions = st.session_state.get("portfolio_positions", {})
    pos_value = 0.0
    for pos in positions.values():
        try:
            pos_value += float(pos.get("quantity", 0.0)) * float(pos.get("current_price", 0.0))
        except Exception:
            continue
    return cash + pos_value


def update_portfolio_prices(prices: dict[str, float]) -> None:
    """Update session positions with latest prices and unrealized PnL."""

    positions = st.session_state.get("portfolio_positions", {})
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


def add_snapshot() -> None:
    """Store a timestamped portfolio snapshot with drawdown metrics."""

    tv = get_portfolio_value()
    peak = float(st.session_state.get("portfolio_peak", tv))
    if tv > peak:
        peak = tv
    st.session_state.portfolio_peak = peak

    dd = (peak - tv) / peak * 100 if peak > 0 else 0.0
    snapshots = st.session_state.get("portfolio_snapshots", [])
    snapshots.append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_value": round(tv, 2),
            "cash": round(float(st.session_state.get("portfolio_cash", 0.0)), 2),
            "drawdown_pct": round(dd, 2),
        }
    )
    st.session_state.portfolio_snapshots = snapshots
