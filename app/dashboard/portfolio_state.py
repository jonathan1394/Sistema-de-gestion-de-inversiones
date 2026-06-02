"""Shared portfolio state helpers for Streamlit dashboard — delegates to helpers."""

from __future__ import annotations

import logging

import streamlit as st

from app.dashboard.helpers import add_snapshot as _add_snapshot
from app.dashboard.helpers import get_portfolio_value as _get_portfolio_value
from app.dashboard.helpers import update_portfolio_prices as _update_portfolio_prices

logger = logging.getLogger(__name__)


def get_portfolio_value() -> float:
    """Return current portfolio value from cash plus marked-to-market positions."""
    return _get_portfolio_value(st.session_state)


def update_portfolio_prices(prices: dict[str, float]) -> None:
    """Update session positions with latest prices and unrealized PnL."""
    _update_portfolio_prices(st.session_state, prices)


def add_snapshot() -> None:
    """Store a timestamped portfolio snapshot with drawdown metrics."""
    _add_snapshot(st.session_state)
