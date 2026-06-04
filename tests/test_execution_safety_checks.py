"""Tests for app/execution/safety_checks.py."""

from unittest.mock import MagicMock

from app.config import AppConfig, BinanceConfig, DatabaseConfig
from app.execution.binance_executor import PermissionCheck
from app.execution.safety_checks import (
    check_binance_permissions,
    check_kill_switch,
    check_market_conditions,
    check_mode,
    check_order_size,
    run_safety_checks,
)


def _make_config(mode="paper", kill_switch=False):
    return AppConfig(
        mode=mode,
        kill_switch=kill_switch,
        binance=BinanceConfig(
            base_url="https://api.binance.com",
            request_timeout_seconds=20,
            max_retries=3,
            retry_delay_seconds=1.5,
        ),
        database=DatabaseConfig(path="/tmp/test.db"),
    )


class TestCheckMode:
    def test_valid_modes(self):
        for mode in ("analysis", "backtest", "paper", "real_manual", "real_auto_limited"):
            config = _make_config(mode=mode)
            result = check_mode(config)
            assert result.safe, f"Mode {mode} should be safe"

    def test_invalid_mode(self):
        config = _make_config(mode="invalid_mode")
        result = check_mode(config)
        assert not result.safe
        assert "Invalid mode" in result.reason

    def test_real_auto_limited_warns(self):
        config = _make_config(mode="real_auto_limited")
        result = check_mode(config)
        assert result.safe
        assert len(result.warnings) > 0


class TestCheckKillSwitch:
    def test_kill_switch_active_blocks(self):
        config = _make_config(kill_switch=True)
        result = check_kill_switch(config)
        assert not result.safe
        assert "Kill switch" in result.reason

    def test_kill_switch_inactive_allows(self):
        config = _make_config(kill_switch=False)
        result = check_kill_switch(config)
        assert result.safe


class TestCheckBinancePermissions:
    def test_blocks_withdraw_permission(self):
        executor = MagicMock()
        executor.validate_permissions.return_value = PermissionCheck(
            can_trade=True,
            can_withdraw_assets=True,
            read_only=False,
            valid=True,
        )

        result = check_binance_permissions(executor)

        assert not result.safe
        assert "withdrawal permission" in result.reason

    def test_warns_read_only_key(self):
        executor = MagicMock()
        executor.validate_permissions.return_value = PermissionCheck(
            can_trade=False,
            can_withdraw_assets=False,
            read_only=True,
            valid=True,
        )

        result = check_binance_permissions(executor)

        assert result.safe
        assert result.warnings


class TestCheckOrderSize:
    def test_valid_order(self):
        result = check_order_size(quantity=0.0005, price=50000, capital=1000)
        assert result.safe

    def test_rejects_zero_quantity(self):
        result = check_order_size(quantity=0, price=50000, capital=1000)
        assert not result.safe

    def test_rejects_oversized_order(self):
        result = check_order_size(quantity=1.0, price=50000, capital=1000, max_position_pct=0.03)
        assert not result.safe
        assert "exceeds max" in result.reason


class TestCheckMarketConditions:
    def test_normal_deviation(self):
        result = check_market_conditions(
            current_price=100.0, reference_price=100.5, max_deviation_pct=1.0
        )
        assert result.safe

    def test_excessive_deviation(self):
        result = check_market_conditions(
            current_price=100.0, reference_price=105.0, max_deviation_pct=1.0
        )
        assert not result.safe
        assert "deviation" in result.reason.lower()

    def test_rejects_invalid_prices(self):
        result = check_market_conditions(current_price=0, reference_price=100)
        assert not result.safe


class TestRunSafetyChecks:
    def test_blocks_when_kill_switch_active(self):
        config = _make_config(mode="paper", kill_switch=True)
        result = run_safety_checks(config)
        assert not result.safe

    def test_blocks_invalid_mode(self):
        config = _make_config(mode="garbage")
        result = run_safety_checks(config)
        assert not result.safe

    def test_passes_valid_paper_mode(self):
        config = _make_config(mode="paper", kill_switch=False)
        result = run_safety_checks(config)
        assert result.safe

    def test_executor_none_is_ok(self):
        config = _make_config(mode="paper", kill_switch=False)
        result = run_safety_checks(config, executor=None)
        assert result.safe
