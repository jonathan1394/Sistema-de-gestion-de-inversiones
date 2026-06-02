"""Tests for app/strategies/base_strategy.py."""

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult


class ConcreteStrategy(BaseStrategy):
    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        return StrategyResult(signals=[])


class TestSignal:
    def test_signal_defaults(self):
        sig = Signal(
            symbol="BTCUSDT",
            timestamp=pd.Timestamp("2024-01-01"),
            action="BUY",
            price=50000.0,
            reason="test",
        )
        assert sig.confidence == 0.5
        assert sig.risk_score == 0.5
        assert sig.stop_loss is None
        assert sig.take_profit is None
        assert sig.position_size_pct is None

    def test_signal_with_all_fields(self):
        sig = Signal(
            symbol="ETHUSDT",
            timestamp=pd.Timestamp("2024-01-01"),
            action="SELL",
            price=3000.0,
            reason="test",
            confidence=0.8,
            risk_score=0.3,
            stop_loss=2900.0,
            take_profit=3200.0,
            position_size_pct=0.02,
        )
        assert sig.confidence == 0.8
        assert sig.stop_loss == 2900.0


class TestStrategyResult:
    def test_empty_result(self):
        result = StrategyResult()
        assert result.signals == []

    def test_result_with_signals(self):
        sig = Signal(
            symbol="BTCUSDT",
            timestamp=pd.Timestamp("2024-01-01"),
            action="BUY",
            price=50000.0,
            reason="test",
        )
        result = StrategyResult(signals=[sig])
        assert len(result.signals) == 1


class TestBaseStrategy:
    def test_cannot_instantiate_directly(self):
        try:
            BaseStrategy()
            instantiated = True
        except TypeError:
            instantiated = False
        assert not instantiated

    def test_concrete_strategy_works(self):
        strategy = ConcreteStrategy(parameters={"fast": 20, "slow": 50})
        assert strategy.parameters == {"fast": 20, "slow": 50}
        data = pd.DataFrame({"close": [1, 2, 3]})
        result = strategy.generate_signals(data)
        assert isinstance(result, StrategyResult)
        assert result.signals == []

    def test_default_parameters(self):
        strategy = ConcreteStrategy()
        assert strategy.parameters == {}
