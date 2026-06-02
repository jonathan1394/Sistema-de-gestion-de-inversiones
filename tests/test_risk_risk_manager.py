"""Tests for app/risk/risk_manager.py."""

from app.risk.circuit_breakers import CircuitBreakers
from app.risk.exposure_limits import PortfolioState
from app.risk.risk_manager import RiskManager, TradeProposal


def _proposal(capital: float = 1000.0) -> TradeProposal:
    return TradeProposal(symbol="BTCUSDT", direction="long", entry_price=50000, capital=capital)


def _portfolio() -> PortfolioState:
    return PortfolioState(total_capital=1000, cash=1000, positions={})


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
