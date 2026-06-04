"""Tests for Monte Carlo simulation (app/backtesting/monte_carlo.py)."""

from __future__ import annotations

import pandas as pd

from app.backtesting.engine import BacktestResult, TradeRecord
from app.backtesting.monte_carlo import (
    MonteCarloPercentiles,
    MonteCarloResult,
    _compute_metrics_from_pnl_list,
    monte_carlo_simulate,
)


def _make_result(
    pnl_pcts: list[float],
    capital: float = 1000.0,
    interval: str = "1h",
) -> BacktestResult:
    trades: list[TradeRecord] = []
    for i, pnl in enumerate(pnl_pcts):
        trades.append(
            TradeRecord(
                symbol="BTCUSDT",
                side="BUY",
                entry_time=pd.Timestamp(f"2020-01-0{i + 1}"),
                exit_time=pd.Timestamp(f"2020-01-0{i + 2}"),
                entry_price=100,
                exit_price=100 * (1 + pnl / 100),
                quantity=capital / 100,
                fees=0.0,
                pnl=pnl,
                pnl_pct=pnl / 100,
                reason_entry="test",
                reason_exit="test",
                status="closed",
                hold_bars=1,
                direction="long",
            )
        )
    total_pnl = sum(pnl_pcts) if pnl_pcts else 0
    n = len(pnl_pcts) if pnl_pcts else 1
    return BacktestResult(
        symbol="BTCUSDT",
        interval=interval,
        initial_capital=capital,
        final_capital=capital * (1 + total_pnl / 100 / n),
        total_fees=0.0,
        trades=trades,
        equity_curve=pd.Series([capital] * (n + 1)),
        strategy_name="Test",
        parameters={},
    )


class TestComputeMetricsFromPnlList:
    def test_all_profitable(self):
        metrics = _compute_metrics_from_pnl_list(
            [1.0, 2.0, 1.5], initial_capital=1000, annualization_factor=365, total_bars=3
        )
        assert metrics.roi_pct > 0
        assert metrics.roi_pct > 4.0  # compound of 1%, 2%, 1.5% > 4%
        assert metrics.win_rate == 100.0
        assert metrics.losing_trades == 0

    def test_all_losing(self):
        metrics = _compute_metrics_from_pnl_list(
            [-1.0, -2.0, -1.5], initial_capital=1000, annualization_factor=365, total_bars=3
        )
        assert metrics.roi_pct < 0
        assert metrics.win_rate == 0.0
        assert metrics.winning_trades == 0

    def test_mixed(self):
        metrics = _compute_metrics_from_pnl_list(
            [5.0, -2.0, 3.0, -1.0], initial_capital=1000, annualization_factor=365, total_bars=4
        )
        assert metrics.total_trades == 4
        assert metrics.winning_trades == 2
        assert metrics.losing_trades == 2
        assert metrics.win_rate == 50.0

    def test_empty(self):
        metrics = _compute_metrics_from_pnl_list(
            [], initial_capital=1000, annualization_factor=365, total_bars=0
        )
        assert metrics.roi_pct == 0.0


class TestMonteCarloPercentiles:
    def test_properties(self):
        p = MonteCarloPercentiles(p5=-5.0, p50=10.0, p95=25.0)
        assert p.downside == -5.0
        assert p.median == 10.0
        assert p.upside == 25.0


class TestMonteCarloSimulate:
    def test_returns_result_object(self):
        result = _make_result([1.0, -0.5, 2.0, 0.5, -1.0])
        mc = monte_carlo_simulate(result, n_simulations=100, seed=42)
        assert isinstance(mc, MonteCarloResult)
        assert mc.n_simulations == 100

    def test_percentiles_are_ordered(self):
        result = _make_result([2.0, -1.0, 1.5, -0.5, 3.0, -2.0, 1.0])
        mc = monte_carlo_simulate(result, n_simulations=200, seed=42)
        assert mc.roi_pct.p5 <= mc.roi_pct.p50
        assert mc.roi_pct.p50 <= mc.roi_pct.p95

    def test_probability_of_profit(self):
        result = _make_result([1.0, 2.0, 1.5, 0.5])
        mc = monte_carlo_simulate(result, n_simulations=200, seed=42)
        assert mc.probability_of_profit > 0.5

    def test_no_trades_returns_empty(self):
        result = _make_result([])
        mc = monte_carlo_simulate(result, n_simulations=100)
        assert mc.n_simulations == 0

    def test_summary_dict(self):
        result = _make_result([1.0, -0.5, 2.0, 0.5])
        mc = monte_carlo_simulate(result, n_simulations=100, seed=42)
        s = mc.summary
        assert "actual_roi_pct" in s
        assert "roi_p50" in s
        assert "prob_profit" in s
        assert "worst_roi" in s

    def test_deterministic_seed(self):
        result = _make_result([1.0, -0.5, 2.0, 0.5, -1.0, 0.3, -0.2, 1.2])
        mc1 = monte_carlo_simulate(result, n_simulations=100, seed=42)
        mc2 = monte_carlo_simulate(result, n_simulations=100, seed=42)
        assert mc1.roi_pct.p50 == mc2.roi_pct.p50

    def test_large_simulation(self):
        result = _make_result([0.5, -0.3, 1.0, -0.2, 0.8])
        mc = monte_carlo_simulate(result, n_simulations=500, seed=42)
        assert mc.n_simulations == 500
        assert len(mc.all_roi_pct) == 500
