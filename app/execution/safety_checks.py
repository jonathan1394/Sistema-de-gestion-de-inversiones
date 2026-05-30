"""Safety checks executed before any live or paper order flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import AppConfig
from app.execution.binance_executor import BinanceExecutor, PermissionCheck


@dataclass
class SafetyResult:
    safe: bool = True
    reason: str = ""
    warnings: list[str] = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


def check_mode(config: AppConfig) -> SafetyResult:
    """Validate configured operation mode and emit mode-related warnings."""
    allowed_modes = ("analysis", "backtest", "paper", "real_manual", "real_auto_limited")
    if config.mode not in allowed_modes:
        return SafetyResult(
            safe=False,
            reason=f"Invalid mode '{config.mode}'. Allowed: {', '.join(allowed_modes)}",
        )

    warnings: list[str] = []
    if config.mode == "real_auto_limited":
        warnings.append("Real automated limited trading mode active")

    return SafetyResult(safe=True, warnings=warnings)


def check_kill_switch(config: AppConfig) -> SafetyResult:
    """Block execution when the global kill switch is enabled."""
    if config.kill_switch:
        return SafetyResult(
            safe=False,
            reason="Kill switch is active — all trading blocked",
        )
    return SafetyResult(safe=True)


def check_binance_permissions(executor: BinanceExecutor) -> SafetyResult:
    """Ensure API key permissions are valid and non-withdrawable."""
    try:
        perms = executor.validate_permissions()
    except Exception as e:
        return SafetyResult(safe=False, reason=f"Permission check failed: {e}")

    if not perms.valid:
        return SafetyResult(safe=False, reason=perms.message)

    if perms.can_withdraw:
        return SafetyResult(
            safe=False,
            reason="CRITICAL: API key has withdrawal permission. Disable immediately.",
        )

    warnings: list[str] = []
    if not perms.can_trade:
        warnings.append("API key is read-only — trading not possible")

    return SafetyResult(safe=True, warnings=warnings)


def check_order_size(
    quantity: float,
    price: float,
    capital: float,
    max_position_pct: float = 0.03,
) -> SafetyResult:
    """Validate that order notional stays under configured position limits."""
    if quantity <= 0:
        return SafetyResult(safe=False, reason="Quantity must be positive")

    order_value = quantity * price
    max_position_value = capital * max_position_pct

    if order_value > max_position_value:
        return SafetyResult(
            safe=False,
            reason=f"Order value ${order_value:.2f} exceeds max ${max_position_value:.2f} "
                   f"({max_position_pct:.1%} of capital)",
        )

    return SafetyResult(safe=True)


def check_market_conditions(
    current_price: float,
    reference_price: float,
    max_deviation_pct: float = 1.0,
) -> SafetyResult:
    """Reject execution when price deviates too far from reference."""
    if current_price <= 0 or reference_price <= 0:
        return SafetyResult(safe=False, reason="Invalid prices")

    deviation = abs(current_price - reference_price) / reference_price * 100
    if deviation > max_deviation_pct:
        return SafetyResult(
            safe=False,
            reason=f"Price deviation {deviation:.2f}% exceeds max {max_deviation_pct:.2f}%",
        )

    return SafetyResult(safe=True)


def run_safety_checks(  # noqa: risk validation before execution
    config: AppConfig,
    executor: Optional[BinanceExecutor] = None,
) -> SafetyResult:
    """Run mode, kill-switch, and optional exchange permission checks."""
    mode_check = check_mode(config)
    if not mode_check.safe:
        return mode_check

    kill_check = check_kill_switch(config)
    if not kill_check.safe:
        return kill_check

    all_warnings: list[str] = []
    if mode_check.warnings:
        all_warnings.extend(mode_check.warnings)
    if kill_check.warnings:
        all_warnings.extend(kill_check.warnings)

    if executor is not None:
        binance_check = check_binance_permissions(executor)
        if not binance_check.safe:
            return binance_check
        if binance_check.warnings:
            all_warnings.extend(binance_check.warnings)

    return SafetyResult(safe=True, warnings=all_warnings)
