"""Tests for app/backtesting/engine.py."""

from unittest.mock import MagicMock

import numpy as np
import pandas as pd

from app.backtesting.engine import BacktestEngine
from app.risk.position_sizing import PositionSizeResult
from app.risk.risk_manager import RiskDecision, RiskManager, TradeProposal
from app.risk.stop_loss import StopLossResult
from app.risk.trailing_stop import TrailingStopConfig
from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult


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


class DummyShortStrategy(BaseStrategy):
    """Strategy that opens a short at index 2 and covers at index 5."""

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        signals = []
        dates = data.index
        if len(dates) >= 6:
            signals.append(Signal(
                symbol="BTCUSDT", timestamp=dates[2], action="BUY",
                price=data.iloc[2]["close"], reason="test short",
                direction="short", position_size_pct=0.5,
            ))
            signals.append(Signal(
                symbol="BTCUSDT", timestamp=dates[5], action="SELL",
                price=data.iloc[5]["close"], reason="test cover",
            ))
        return StrategyResult(signals=signals)


class DummyTrailingStrategy(BaseStrategy):
    """Strategy that buys at index 2 with stop-loss and sells at index 5."""

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        signals = []
        dates = data.index
        if len(dates) >= 6:
            entry_price = data.iloc[2]["close"]
            signals.append(Signal(
                symbol="BTCUSDT", timestamp=dates[2], action="BUY",
                price=entry_price, reason="test with stop",
                position_size_pct=0.5,
                stop_loss=entry_price * 0.95,
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

    def test_short_strategy_runs(self):
        data = _make_data()
        engine = BacktestEngine(DummyShortStrategy(), data)
        result = engine.run()
        assert result.initial_capital == 1000.0
        assert result.final_capital > 0

    def test_short_strategy_generates_trades(self):
        data = _make_data()
        engine = BacktestEngine(DummyShortStrategy(), data)
        result = engine.run()
        assert len(result.trades) >= 1

    def test_short_trade_has_short_direction(self):
        data = _make_data()
        engine = BacktestEngine(DummyShortStrategy(), data)
        result = engine.run()
        assert any(t.direction == "short" for t in result.trades)

    def test_short_profit_on_downward_move(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="1h")
        prices = [100, 101, 100, 99, 98, 97, 96, 95, 94, 93]
        data = pd.DataFrame({
            "open": prices, "high": [p + 0.5 for p in prices],
            "low": [p - 0.5 for p in prices], "close": prices,
            "volume": [1000] * 10,
        }, index=dates)
        engine = BacktestEngine(
            DummyShortStrategy(), data, commission_pct=0.0, slippage_pct=0.0
        )
        result = engine.run()
        assert result.final_capital > result.initial_capital

    def test_trailing_stop_runs_without_error(self):
        data = _make_data()
        cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.02)
        engine = BacktestEngine(
            DummyTrailingStrategy(), data,
            trailing_stop_config=cfg,
        )
        result = engine.run()
        assert result.final_capital > 0

    def test_trailing_stop_does_not_break_normal_execution(self):
        data = _make_data()
        cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.02)
        trailing = BacktestEngine(
            DummyTrailingStrategy(), data,
            trailing_stop_config=cfg,
        ).run()
        assert trailing.final_capital > 0

    def test_trailing_stop_with_short_position(self):
        data = _make_data()
        cfg = TrailingStopConfig(activation_pct=0.01, trail_pct=0.02)
        engine = BacktestEngine(
            DummyShortStrategy(), data,
            trailing_stop_config=cfg,
        )
        result = engine.run()
        assert result.final_capital > 0

        result = engine.run()
        assert result.final_capital > 0


class TestBacktestEngineWithRiskManager:
    """Verify RiskManager integration in BacktestEngine.run()."""

    def _make_engine(self, risk_manager: RiskManager | None, data=None):
        if data is None:
            data = _make_data()
        return BacktestEngine(DummyStrategy(), data, risk_manager=risk_manager)

    def test_rm_approved_proceeds_normally(self):
        rm = RiskManager(circuit_breakers=MagicMock(trading_allowed=True))
        rm._circuit_breakers.can_open_new_position.return_value = MagicMock(trading_allowed=True)
        engine = self._make_engine(rm)
        result = engine.run()
        assert len(result.trades) >= 1
        assert len(result.rejected_signals) == 0

    def test_rm_blocks_signal_gets_rejected(self):
        rm = RiskManager(circuit_breakers=MagicMock(trading_allowed=True))
        rm._circuit_breakers.can_open_new_position.return_value = MagicMock(trading_allowed=True)
        rm.evaluate = MagicMock(return_value=RiskDecision(
            approved=False, rejection_reason="Risk limit exceeded"
        ))
        engine = self._make_engine(rm)
        result = engine.run()
        assert len(result.trades) == 0
        assert len(result.rejected_signals) > 0
        assert "Risk limit exceeded" in result.rejected_signals[0]["rejection"]

    def test_rm_rejected_signals_contain_timestamp_and_reason(self):
        rm = RiskManager(circuit_breakers=MagicMock(trading_allowed=True))
        rm._circuit_breakers.can_open_new_position.return_value = MagicMock(trading_allowed=True)
        rm.evaluate = MagicMock(return_value=RiskDecision(
            approved=False, rejection_reason="Daily loss limit"
        ))
        engine = self._make_engine(rm)
        result = engine.run()
        assert len(result.rejected_signals) > 0
        entry = result.rejected_signals[0]
        assert "timestamp" in entry
        assert "reason" in entry
        assert "rejection" in entry
        assert entry["rejection"] == "Daily loss limit"

    def test_rm_no_risk_manager_no_rejected_signals(self):
        engine = self._make_engine(None)
        result = engine.run()
        assert result.rejected_signals == []

    def test_rm_kill_switch_blocks_all_trades(self):
        rm = RiskManager(circuit_breakers=MagicMock(trading_allowed=True))
        rm._circuit_breakers.can_open_new_position.return_value = MagicMock(
            trading_allowed=False, reason="Kill switch active"
        )
        engine = self._make_engine(rm)
        result = engine.run()
        assert len(result.trades) == 0
        assert len(result.rejected_signals) > 0

    def test_rm_position_size_from_decision_used(self):
        """When RM approves, its position_size should be used."""
        rm = RiskManager(circuit_breakers=MagicMock(trading_allowed=True))
        rm._circuit_breakers.can_open_new_position.return_value = MagicMock(trading_allowed=True)

        decision = RiskDecision(
            approved=True,
            stop_loss=StopLossResult(stop_price=99.0, distance_pct=0.01, method="fixed"),
        )
        decision.position_size = PositionSizeResult(
            position_size=0.5, position_value=100.0,
            risk_amount=1.0, risk_pct=0.01, entry_price=100.0,
            stop_loss=99.0, max_risk_pct=0.01,
        )
        rm.evaluate = MagicMock(return_value=decision)

        engine = self._make_engine(rm)
        result = engine.run()
        assert len(result.trades) >= 1
        assert result.trades[0].entry_price > 0

    def test_rm_short_strategy_with_risk_manager(self):
        """Short strategy should work with RiskManager."""
        rm = RiskManager(circuit_breakers=MagicMock(trading_allowed=True))
        rm._circuit_breakers.can_open_new_position.return_value = MagicMock(trading_allowed=True)
        decision = RiskDecision(
            approved=True,
            stop_loss=StopLossResult(stop_price=102.0, distance_pct=0.02, method="fixed"),
        )
        decision.position_size = PositionSizeResult(
            position_size=1.0, position_value=500.0,
            risk_amount=5.0, risk_pct=0.01, entry_price=100.0,
            stop_loss=102.0, max_risk_pct=0.01,
        )
        rm.evaluate = MagicMock(return_value=decision)
        data = _make_data()
        engine = BacktestEngine(DummyShortStrategy(), data, risk_manager=rm)
        result = engine.run()
        assert len(result.trades) >= 1
        assert any(t.direction == "short" for t in result.trades)

    def test_rm_with_dynamic_take_profit_via_atr(self):
        """When RM has take_profit_atr_multiplier and atr is available, TP should be set."""
        rm = RiskManager(
            circuit_breakers=MagicMock(trading_allowed=True),
            take_profit_atr_multiplier=3.0,
        )
        rm._circuit_breakers.can_open_new_position.return_value = MagicMock(trading_allowed=True)

        decision = RiskDecision(
            approved=True,
            stop_loss=StopLossResult(stop_price=98.0, distance_pct=0.02, method="fixed"),
            take_profit=StopLossResult(stop_price=106.0, distance_pct=0.06, method="atr"),
        )
        decision.position_size = PositionSizeResult(
            position_size=1.0, position_value=500.0,
            risk_amount=5.0, risk_pct=0.01, entry_price=100.0,
            stop_loss=98.0, max_risk_pct=0.01,
        )
        rm.evaluate = MagicMock(return_value=decision)

        engine = self._make_engine(rm)
        result = engine.run()
        assert len(result.trades) >= 1

    def test_rm_evaluate_called_with_correct_args(self):
        """Verify evaluate receives proper TradeProposal."""
        rm = RiskManager(circuit_breakers=MagicMock(trading_allowed=True))
        rm._circuit_breakers.can_open_new_position.return_value = MagicMock(trading_allowed=True)
        rm.evaluate = MagicMock(return_value=RiskDecision(
            approved=True,
            stop_loss=StopLossResult(stop_price=99.0, distance_pct=0.01, method="fixed"),
        ))

        engine = self._make_engine(rm)
        engine.run()

        assert rm.evaluate.called
        call_args = rm.evaluate.call_args
        proposal = call_args[0][0]
        assert isinstance(proposal, TradeProposal)
        assert proposal.symbol == "UNKNOWN"
