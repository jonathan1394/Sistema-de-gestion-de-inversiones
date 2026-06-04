"""Tests for walk-forward optimization (app/backtesting/optimizer.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.backtesting.optimizer import (
    ParamGrid,
    WalkForwardResult,
    _build_param_combinations,
    walk_forward_optimize,
)
from app.strategies.moving_average import MovingAverageCrossover
from app.strategies.rsi_strategy import RSIStrategy


@pytest.fixture
def sample_data() -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=500, freq="h")
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.normal(0, 0.5, 500))
    return pd.DataFrame(
        {
            "timestamp": dates,
            "open": close - 0.1,
            "high": close + 0.3,
            "low": close - 0.3,
            "close": close,
            "volume": np.random.randint(1000, 5000, 500),
        }
    )


class TestParamGrid:
    def test_single_param(self):
        grid = [ParamGrid(name="fast_period", values=[10, 20, 30])]
        combos = _build_param_combinations(grid)
        assert len(combos) == 3
        assert combos[0] == {"fast_period": 10}
        assert combos[1] == {"fast_period": 20}

    def test_two_params(self):
        grid = [
            ParamGrid(name="fast_period", values=[10, 20]),
            ParamGrid(name="slow_period", values=[50, 100]),
        ]
        combos = _build_param_combinations(grid)
        assert len(combos) == 4
        assert {"fast_period": 10, "slow_period": 50} in combos
        assert {"fast_period": 20, "slow_period": 100} in combos

    def test_empty_values(self):
        grid = [ParamGrid(name="p", values=[])]
        assert _build_param_combinations(grid) == []


class TestWalkForwardOptimize:
    def test_returns_walkforward_result(self, sample_data):
        result = walk_forward_optimize(
            strategy_class=MovingAverageCrossover,
            param_grid=[
                ParamGrid(name="fast_period", values=[10, 20]),
                ParamGrid(name="slow_period", values=[50, 100]),
            ],
            data=sample_data,
            symbol="BTCUSDT",
            interval="1h",
            n_windows=2,
            initial_capital=1000,
        )
        assert isinstance(result, WalkForwardResult)
        assert result.strategy_name == "MovingAverageCrossover"
        assert result.total_windows > 0

    def test_windows_have_expected_fields(self, sample_data):
        result = walk_forward_optimize(
            strategy_class=MovingAverageCrossover,
            param_grid=[ParamGrid(name="fast_period", values=[20])],
            data=sample_data,
            n_windows=2,
            initial_capital=1000,
        )
        for w in result.windows:
            assert hasattr(w, "train_start")
            assert hasattr(w, "test_end")
            assert isinstance(w.best_params, dict)
            assert hasattr(w.train_metrics, "sharpe_ratio")
            assert hasattr(w.test_metrics, "sharpe_ratio")
            assert hasattr(w.train_result, "trades")
            assert hasattr(w.test_result, "trades")

    def test_avg_metrics_computed(self, sample_data):
        result = walk_forward_optimize(
            strategy_class=RSIStrategy,
            param_grid=[
                ParamGrid(name="rsi_period", values=[14]),
                ParamGrid(name="oversold", values=[30]),
                ParamGrid(name="overbought", values=[70]),
            ],
            data=sample_data,
            n_windows=2,
            initial_capital=1000,
        )
        assert result.avg_train_metrics is not None
        assert result.avg_test_metrics is not None
        assert 0 <= result.consistency_score <= 1

    def test_summary_dict(self, sample_data):
        result = walk_forward_optimize(
            strategy_class=MovingAverageCrossover,
            param_grid=[ParamGrid(name="fast_period", values=[20])],
            data=sample_data,
            n_windows=2,
        )
        s = result.summary
        assert "strategy" in s
        assert "consistency_score" in s
        assert "avg_test_sharpe" in s

    def test_insufficient_data_returns_empty(self):
        small_data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2020-01-01", periods=10, freq="h"),
                "open": [100] * 10,
                "high": [101] * 10,
                "low": [99] * 10,
                "close": [100] * 10,
                "volume": [1000] * 10,
            }
        )
        result = walk_forward_optimize(
            strategy_class=MovingAverageCrossover,
            param_grid=[ParamGrid(name="fast_period", values=[20])],
            data=small_data,
            n_windows=2,
        )
        assert result.total_windows == 0

    def test_best_params_overall(self, sample_data):
        result = walk_forward_optimize(
            strategy_class=MovingAverageCrossover,
            param_grid=[
                ParamGrid(name="fast_period", values=[10, 20]),
                ParamGrid(name="slow_period", values=[50, 100]),
            ],
            data=sample_data,
            n_windows=2,
        )
        assert isinstance(result.best_params_overall, dict)
        if result.best_params_overall:
            assert "fast_period" in result.best_params_overall

    def test_empty_param_grid_uses_defaults(self, sample_data):
        result = walk_forward_optimize(
            strategy_class=MovingAverageCrossover,
            param_grid=[],
            data=sample_data,
            n_windows=2,
        )
        assert result.total_windows > 0
        assert result.best_params_overall == {}
