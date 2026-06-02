"""Tests for app/risk/circuit_breakers.py."""

from app.risk.circuit_breakers import CircuitBreakers


def test_daily_loss_limit_blocks_trading():
    breakers = CircuitBreakers(
        max_daily_loss_pct=0.03,
        max_weekly_loss_pct=0.07,
        kill_switch=False,
    )

    breakers.record_trade(pnl_pct=-0.031, capital=1000)
    result = breakers.check_trading_allowed(capital=1000)

    assert not result.trading_allowed
    assert "Daily loss" in result.reason


def test_weekly_loss_limit_blocks_trading():
    breakers = CircuitBreakers(
        max_daily_loss_pct=0.10,
        max_weekly_loss_pct=0.07,
        kill_switch=False,
    )

    breakers.record_trade(pnl_pct=-0.071, capital=1000)
    result = breakers.check_trading_allowed(capital=1000)

    assert not result.trading_allowed
    assert "Weekly loss" in result.reason


def test_loss_inside_limits_allows_trading():
    breakers = CircuitBreakers(
        max_daily_loss_pct=0.03,
        max_weekly_loss_pct=0.07,
        kill_switch=False,
    )

    breakers.record_trade(pnl_pct=-0.01, capital=1000)
    result = breakers.check_trading_allowed(capital=1000)

    assert result.trading_allowed
