"""Tests for app/backtesting/metrics.py."""

from __future__ import annotations

import pandas as pd

from app.backtesting.engine import BacktestResult, TradeRecord
from app.backtesting.metrics import compute_metrics


def _result(equity_values: list[float], trades: list[TradeRecord]) -> BacktestResult:
    index = pd.date_range("2024-01-01", periods=len(equity_values), freq="D", tz="UTC")
    return BacktestResult(
        symbol="BTCUSDT",
        interval="1d",
        initial_capital=equity_values[0],
        final_capital=equity_values[-1],
        total_fees=1.5,
        trades=trades,
        equity_curve=pd.Series(equity_values, index=index),
        strategy_name="test",
        parameters={},
    )


def test_compute_metrics_with_winning_trades():
    trades = [
        TradeRecord(symbol="BTCUSDT", side="BUY", entry_time=pd.Timestamp("2024-01-01"), pnl=100, pnl_pct=0.10, hold_bars=2),
        TradeRecord(symbol="BTCUSDT", side="BUY", entry_time=pd.Timestamp("2024-01-02"), pnl=50, pnl_pct=0.05, hold_bars=1),
    ]

    metrics = compute_metrics(_result([1000, 1050, 1150], trades))

    assert metrics.roi_pct == 15.0
    assert metrics.total_trades == 2
    assert metrics.winning_trades == 2
    assert metrics.win_rate == 100.0
    assert metrics.profit_factor == float("inf")
    assert metrics.total_fees == 1.5


def test_compute_metrics_with_losses_and_drawdown():
    trades = [
        TradeRecord(symbol="BTCUSDT", side="BUY", entry_time=pd.Timestamp("2024-01-01"), pnl=-100, pnl_pct=-0.10, hold_bars=1),
        TradeRecord(symbol="BTCUSDT", side="BUY", entry_time=pd.Timestamp("2024-01-02"), pnl=-50, pnl_pct=-0.05, hold_bars=1),
    ]

    metrics = compute_metrics(_result([1000, 500, 600], trades))

    assert metrics.roi_pct == -40.0
    assert metrics.max_drawdown_pct == -50.0
    assert metrics.losing_trades == 2
    assert metrics.consecutive_losses == 2
    assert metrics.gross_loss == 150.0


def test_compute_metrics_handles_empty_trades():
    metrics = compute_metrics(_result([1000, 1010, 1020], []))

    assert metrics.total_trades == 0
    assert metrics.win_rate == 0.0
    assert metrics.final_capital == 1020
