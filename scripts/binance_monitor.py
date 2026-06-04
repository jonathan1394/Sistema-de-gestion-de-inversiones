from __future__ import annotations

import argparse

from loguru import logger

from app.config import load_settings
from app.execution import (
    BinanceExecutor,
    check_kill_switch,
    check_mode,
    run_safety_checks,
)
from app.logging_setup import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Binance account monitor and executor")
    parser.add_argument(
        "--action",
        default="status",
        choices=["status", "balances", "orders", "history"],
        help="Action to perform",
    )
    parser.add_argument("--symbol", default="", help="Symbol filter (e.g. BTCUSDT)")
    parser.add_argument("--limit", type=int, default=20, help="History limit")
    parser.add_argument("--settings", default="settings.yaml", help="Settings YAML path")
    parser.add_argument("--check", action="store_true", help="Run safety checks only")
    return parser.parse_args()


def format_balances(balances: list) -> str:
    lines = ["Balances:"]
    for b in balances:
        lines.append(
            f"  {b.asset:8s}  Free: {b.free:>12.6f}  Locked: {b.locked:>12.6f}  Total: {b.total:>12.6f}"
        )
    return "\n".join(lines)


def format_orders(orders: list) -> str:
    if not orders:
        return "No orders found."
    lines = ["Orders:"]
    lines.append(
        f"  {'ID':>8s}  {'Symbol':10s}  {'Side':5s}  {'Type':7s}  {'Price':>12s}  {'Qty':>12s}  {'Filled':>12s}  {'Status':12s}"
    )
    for o in orders:
        lines.append(
            f"  {o.order_id:>8d}  {o.symbol:10s}  {o.side:5s}  {o.type:7s}  {o.price:>12.2f}  {o.orig_qty:>12.6f}  {o.executed_qty:>12.6f}  {o.status:12s}"
        )
    return "\n".join(lines)


def _warn_missing_credentials(api_key: str, api_secret: str) -> None:
    if api_key and api_secret:
        return
    logger.warning("BINANCE_API_KEY and BINANCE_API_SECRET not set in .env")
    logger.warning("Set them in secrets.example.env and copy to .env")


def _run_check_only(config, executor) -> bool:
    logger.info("Running safety checks...")
    result = run_safety_checks(config, executor)
    if result.safe:
        logger.info("All safety checks passed")
    else:
        logger.error("Safety check failed: %s", result.reason)
    for warning in result.warnings:
        logger.warning(warning)
    return True


def _preflight(config, api_key: str) -> tuple[bool, str]:
    mode_result = check_mode(config)
    kill_result = check_kill_switch(config)
    logger.info("Mode: %s", config.mode)
    logger.info("Kill Switch: %s", "ACTIVE" if config.kill_switch else "Inactive")

    if not api_key:
        return False, "\nNo API key configured. Read-only mode not available."
    if not mode_result.safe:
        return False, f"Mode check failed: {mode_result.reason}"
    if not kill_result.safe:
        return False, f"Kill switch active: {kill_result.reason}"
    return True, ""


def _check_connectivity_and_permissions(executor) -> tuple[bool, str]:
    if not executor.check_connectivity():
        return False, "Cannot connect to Binance API"
    logger.info("Connected to Binance API")

    perms = executor.validate_permissions()
    logger.info("API Permissions: %s", "valid" if perms.valid else "invalid")
    logger.info("  Trade: %s", "enabled" if perms.can_trade else "disabled")
    logger.info(
        "  Withdraw: %s (should be disabled)",
        "enabled" if perms.can_withdraw_assets else "disabled",
    )
    logger.info("  Read-only: %s", "yes" if perms.read_only else "no")

    if perms.can_withdraw_assets:
        return False, "\n⚠️  CRITICAL: Withdrawal permission enabled! Disable immediately."
    return True, ""


def _print_status(executor) -> None:
    balances = executor.get_balances()
    total_usdt = next((b.total for b in balances if b.asset == "USDT"), 0.0)
    orders = executor.get_open_orders()
    print(f"\nUSDT Balance: ${total_usdt:.2f}")
    print(f"Open Orders: {len(orders)}")
    if orders:
        print(f"\n{format_orders(orders)}")


def _run_action(args: argparse.Namespace, executor) -> None:
    if args.action == "balances":
        print(f"\n{format_balances(executor.get_balances())}")
        return
    if args.action == "orders":
        print(f"\n{format_orders(executor.get_open_orders(args.symbol))}")
        return
    if args.action == "history":
        if not args.symbol:
            print("--symbol is required for history action")
            return
        orders = executor.get_order_history(args.symbol, args.limit)
        print(f"\n{format_orders(orders)}")
        return
    _print_status(executor)


def main() -> None:
    args = parse_args()
    config = load_settings(args.settings)
    setup_logging()

    api_key = config.binance_api_key
    api_secret = config.binance_api_secret
    _warn_missing_credentials(api_key, api_secret)

    executor = BinanceExecutor(config, api_key, api_secret)

    if args.check:
        _run_check_only(config, executor)
        return

    preflight_ok, preflight_message = _preflight(config, api_key)
    if not preflight_ok:
        print(preflight_message)
        return

    checks_ok, checks_message = _check_connectivity_and_permissions(executor)
    if not checks_ok:
        print(checks_message)
        return

    _run_action(args, executor)


if __name__ == "__main__":
    main()
