"""Tests for app/backtesting/engine.py."""

import pandas as pd
import numpy as np

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult
from app.backtesting.engine import BacktestEngine


class DummyStrategy(BaseStrategy):
    """Strategy that buys at index 2 and sells at index 5 for testing."""

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        signals = []
        dates = data.index
        if len(dates) >= 6:
            signals.append(Signal(
                symbol="BTCUSDT", timestamp=dates[2], action="BUY",
                price=data.iloc[2]["close"], reason="test buy",
                position_size_pct=0.5,
            ))
            signals.append(Signal(
                symbol="BTCUSDT", timestamp=dates[5], action="SELL",
                price=data.iloc[5]["close"], reason="test sell",
            ))
        return StrategyResult(signals=signals)


def _make_data(n=10):
    dates = pd.date_range("2024-01-01", periods=n, freq="1h")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        "open": prices,
        "high": prices + 0.5,
        "low": prices - 0.5,
        "close": prices,
        "volume": np.ones(n) * 1000,
    }, index=dates)


class TestBacktestEngine:
    def test_runs_without_crash(self):
        data = _make_data()
        engine = BacktestEngine(DummyStrategy(), data)
        result = engine.run()
        assert result.initial_capital == 1000.0
        assert result.final_capital > 0

    def test_trades_are_generated(self):
        data = _make_data()
        engine = BacktestEngine(DummyStrategy(), data)
        result = engine.run()
        assert len(result.trades) >= 1

    def test_equity_curve_has_same_length_as_data(self):
        data = _make_data()
        engine = BacktestEngine(DummyStrategy(), data)
        result = engine.run()
        assert len(result.equity_curve) == len(data)

    def test_commissions_are_deducted(self):
        data = _make_data()
        engine_no_fee = BacktestEngine(DummyStrategy(), data, commission_pct=0.0)
        engine_fee = BacktestEngine(DummyStrategy(), data, commission_pct=0.01)
        r1 = engine_no_fee.run()
        r2 = engine_fee.run()
        assert r2.total_fees > 0
        assert r1.final_capital >= r2.final_capital

    def test_slippage_affects_execution_price(self):
        data = _make_data()
        engine = BacktestEngine(
            DummyStrategy(), data, slippage_pct=0.05, commission_pct=0.0
        )
        result = engine.run()
        assert result.final_capital > 0

    def test_backtest_result_fields(self):
        data = _make_data()
        engine = BacktestEngine(DummyStrategy(), data, symbol="BTCUSDT", interval="1h")
        result = engine.run()
        assert result.symbol == "BTCUSDT"
        assert result.interval == "1h"
        assert result.strategy_name == "DummyStrategy"
