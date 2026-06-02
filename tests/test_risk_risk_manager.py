"""Tests for app/risk/risk_manager.py."""

from app.risk.circuit_breakers import CircuitBreakers
from app.risk.exposure_limits import PortfolioState
from app.risk.risk_manager import RiskManager, TradeProposal


def _proposal(capital: float = 1000.0) -> TradeProposal:
    return TradeProposal(symbol="BTCUSDT", direction="long", entry_price=50000, capital=capital)


def _portfolio(total_capital: float = 1000.0) -> PortfolioState:
    return PortfolioState(total_capital=total_capital, cash=total_capital, positions={})


def test_evaluate_all_approved():
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    decision = mgr.evaluate(_proposal(), _portfolio(), stop_loss_price=49000)
    assert decision.approved
    assert decision.position_size is not None
    assert decision.position_size.position_size > 0
    assert decision.stop_loss is not None
    assert decision.stop_loss.stop_price == 49000


def test_circuit_breaker_blocks():
    breakers = CircuitBreakers(kill_switch=True)
    mgr = RiskManager(circuit_breakers=breakers)
    decision = mgr.evaluate(_proposal(), _portfolio(), stop_loss_price=49000)
    assert not decision.approved
    assert "Kill switch" in decision.rejection_reason


def test_circuit_breaker_daily_loss_blocks():
    breakers = CircuitBreakers(max_daily_loss_pct=0.03, kill_switch=False)
    breakers.record_trade(pnl_pct=-0.05, capital=1000)
    mgr = RiskManager(circuit_breakers=breakers)
    decision = mgr.evaluate(_proposal(500), _portfolio(), stop_loss_price=49000)
    assert not decision.approved
    assert "Daily loss" in decision.rejection_reason


def test_stop_loss_price_invalid_rejected():
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    decision = mgr.evaluate(_proposal(), _portfolio(), stop_loss_price=51000)
    assert not decision.approved
    assert decision.rejection_reason != ""


def test_default_stop_loss_used_when_none_provided():
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False), default_stop_loss_pct=0.05)
    decision = mgr.evaluate(_proposal(), _portfolio())
    assert decision.approved
    assert decision.stop_loss is not None
    expected = 50000 * (1 - 0.05)
    assert decision.stop_loss.stop_price == expected


def test_exposure_limit_blocks():
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False), max_asset_pct=0.01, max_total_pct=0.01)
    portfolio = PortfolioState(
        total_capital=1000,
        cash=1000,
        positions={},
    )
    decision = mgr.evaluate(_proposal(1000), portfolio, stop_loss_price=49000)
    assert not decision.approved
    assert "exposure" in decision.rejection_reason.lower()


def test_altcoin_exposure_blocks():
    mgr = RiskManager(
        circuit_breakers=CircuitBreakers(kill_switch=False),
        max_asset_pct=0.10,
        max_total_pct=0.50,
        max_altcoin_pct=0.01,
        altcoin_symbols={"SOLUSDT"},
    )
    alt_proposal = TradeProposal(symbol="SOLUSDT", direction="long", entry_price=150, capital=1000)
    portfolio = PortfolioState(total_capital=1000, cash=1000, positions={})
    decision = mgr.evaluate(alt_proposal, portfolio, stop_loss_price=140)
    assert not decision.approved
    assert "altcoin" in decision.rejection_reason.lower()


def test_zero_capital_rejected():
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    decision = mgr.evaluate(_proposal(capital=0), _portfolio(), stop_loss_price=49000)
    assert not decision.approved


def test_low_confidence_adds_warning():
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    proposal = TradeProposal(
        symbol="BTCUSDT", direction="long", entry_price=50000,
        capital=1000, confidence=0.2,
    )
    decision = mgr.evaluate(proposal, _portfolio(), stop_loss_price=49000)
    assert decision.approved
    assert any("confidence" in w for w in decision.warnings)


def test_evaluation_order_cb_first():
    breakers = CircuitBreakers(kill_switch=True)
    mgr = RiskManager(circuit_breakers=breakers)
    decision = mgr.evaluate(_proposal(), _portfolio(), stop_loss_price=49000)
    assert decision.circuit_breaker is not None
    assert not decision.circuit_breaker.trading_allowed
    assert decision.stop_loss is None
    assert decision.position_size is None
    assert decision.exposure is None


def test_evaluation_order_sl_before_ps():
    """When SL runs (even with invalid price), PS must be set (rejected)."""
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    decision = mgr.evaluate(_proposal(), _portfolio(), stop_loss_price=51000)
    assert decision.stop_loss is not None
    assert decision.position_size is not None
    assert decision.position_size.rejected
    assert decision.exposure is None
    assert not decision.approved


def test_evaluation_order_ps_before_el():
    """When PS fails (invalid direction), EL must be None."""
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    short_proposal = TradeProposal(symbol="BTCUSDT", direction="short", entry_price=50000, capital=1000)
    decision = mgr.evaluate(short_proposal, _portfolio(), stop_loss_price=49000)
    assert decision.position_size is not None
    assert decision.position_size.rejected
    assert decision.exposure is None
    assert not decision.approved


def test_stop_loss_pct_parameter():
    """Passing stop_loss_pct explicitly should be used over default."""
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False), default_stop_loss_pct=0.02)
    decision = mgr.evaluate(_proposal(), _portfolio(), stop_loss_pct=0.05)
    assert decision.approved
    expected = 50000 * (1 - 0.05)
    assert decision.stop_loss is not None
    assert decision.stop_loss.stop_price == expected


def test_stop_loss_pct_too_small_rejected():
    """A stop_loss_pct below minimum should reject."""
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    decision = mgr.evaluate(_proposal(), _portfolio(), stop_loss_pct=0.0001)
    assert not decision.approved
    assert "below minimum" in decision.rejection_reason


def test_very_small_capital_with_relaxed_exposure():
    """Tiny capital + relaxed limits should still approve if size > 0."""
    mgr = RiskManager(
        circuit_breakers=CircuitBreakers(kill_switch=False),
        max_risk_per_trade_pct=0.001,
        max_position_pct=1.0,
        max_asset_pct=1.0,
        max_total_pct=1.0,
    )
    proposal = TradeProposal(symbol="BTCUSDT", direction="long", entry_price=50000, capital=1.0)
    decision = mgr.evaluate(proposal, _portfolio(total_capital=1.0), stop_loss_price=49999)
    assert decision.approved
    assert decision.position_size is not None
    assert decision.position_size.position_value > 0


def test_short_direction_approved():
    """Short direction should pass through risk checks correctly."""
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    proposal = TradeProposal(symbol="BTCUSDT", direction="short", entry_price=50000, capital=1000)
    decision = mgr.evaluate(proposal, _portfolio(), stop_loss_price=51000)
    assert decision.approved
    assert decision.stop_loss is not None
    assert decision.stop_loss.stop_price == 51000


def test_take_profit_dynamic_when_atr_provided():
    """When atr_value and take_profit_atr_multiplier are set, TP should be computed."""
    mgr = RiskManager(
        circuit_breakers=CircuitBreakers(kill_switch=False),
        take_profit_atr_multiplier=3.0,
    )
    decision = mgr.evaluate(_proposal(), _portfolio(), stop_loss_price=49000, atr_value=1000.0)
    assert decision.approved
    assert decision.take_profit is not None
    assert decision.take_profit.stop_price == 50000 + 1000.0 * 3.0


def test_take_profit_not_computed_without_multiplier():
    """No TP when take_profit_atr_multiplier is None."""
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    decision = mgr.evaluate(_proposal(), _portfolio(), stop_loss_price=49000, atr_value=1000.0)
    assert decision.approved
    assert decision.take_profit is None


def test_take_profit_not_computed_without_atr():
    """No TP when atr_value is None even if multiplier is set."""
    mgr = RiskManager(
        circuit_breakers=CircuitBreakers(kill_switch=False),
        take_profit_atr_multiplier=3.0,
    )
    decision = mgr.evaluate(_proposal(), _portfolio(), stop_loss_price=49000)
    assert decision.approved
    assert decision.take_profit is None


def test_trailing_stop_config_property():
    """Getters and setters for trailing_stop_config."""
    from app.risk.trailing_stop import TrailingStopConfig

    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    assert mgr.trailing_stop_config is None

    config = TrailingStopConfig(activation_pct=0.02, trail_pct=0.01)
    mgr.trailing_stop_config = config
    assert mgr.trailing_stop_config is config
    assert mgr.trailing_stop_config.activation_pct == 0.02


def test_take_profit_atr_multiplier_property():
    """Getters and setters for take_profit_atr_multiplier."""
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    assert mgr.take_profit_atr_multiplier is None

    mgr.take_profit_atr_multiplier = 2.5
    assert mgr.take_profit_atr_multiplier == 2.5


def test_circuit_breakers_property():
    """Expose circuit-breaker state and controls via property."""
    breakers = CircuitBreakers(kill_switch=False)
    mgr = RiskManager(circuit_breakers=breakers)
    assert mgr.circuit_breakers is breakers


def test_high_confidence_no_warning():
    """High confidence (>0.3) should not generate warning."""
    mgr = RiskManager(circuit_breakers=CircuitBreakers(kill_switch=False))
    proposal = TradeProposal(
        symbol="BTCUSDT", direction="long", entry_price=50000,
        capital=1000, confidence=0.8,
    )
    decision = mgr.evaluate(proposal, _portfolio(), stop_loss_price=49000)
    assert decision.approved
    assert len(decision.warnings) == 0


def test_adjusted_position_value_set():
    """adjusted_position_value should be set when position_value < max_position_pct * capital."""
    mgr = RiskManager(
        circuit_breakers=CircuitBreakers(kill_switch=False),
        max_position_pct=0.6,
        max_asset_pct=1.0,
        max_total_pct=1.0,
    )
    decision = mgr.evaluate(_proposal(1000), _portfolio(), stop_loss_price=49000)
    assert decision.approved
    assert decision.adjusted_position_value is not None
    assert decision.adjusted_position_value == 500.0  # risk-capped, not max-pct-capped
