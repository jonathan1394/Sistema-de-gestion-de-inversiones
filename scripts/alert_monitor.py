from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

import pandas as pd
import yaml

from app.alerts import (
    Alert,
    AlertEngine,
    AlertRule,
    AlertManager,
    build_alert_manager,
    price_alert_rule,
    signal_alert_rule,
    risk_alert_rule,
    HISTORY_FILE,
)
from app.config import load_settings
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.strategies.base_strategy import Signal
from app.strategies.moving_average import MovingAverageCrossover


def _load_alerts_config() -> dict:
    try:
        with open("settings.yaml") as f:
            raw = yaml.safe_load(f) or {}
        return raw.get("alerts", {})
    except Exception:
        return {}


def _get_current_drawdown(conn: sqlite3.Connection) -> float:
    """Calculate current drawdown from paper snapshots."""
    # Get latest total_value
    latest_row = conn.execute(
        "SELECT total_value FROM paper_snapshots ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    if not latest_row:
        return 0.0
    latest_value = float(latest_row[0])
    
    # Get maximum total_value (peak)
    peak_row = conn.execute(
        "SELECT MAX(total_value) FROM paper_snapshots"
    ).fetchone()
    if not peak_row:
        return 0.0
    peak_value = float(peak_row[0])
    
    if peak_value == 0:
        return 0.0
    drawdown = (peak_value - latest_value) / peak_value * 100.0
    return max(0.0, drawdown)


def _get_latest_price(symbol: str, conn) -> float:
    candles = get_candles(conn, symbol, "4h", limit=1, desc=True)
    return candles[-1].close if candles else 0.0


def _get_signals(symbol: str, conn) -> list[Signal]:
    candles = get_candles(conn, symbol, "4h", limit=200, desc=True)
    if len(candles) < 50:
        return []
    data = pd.DataFrame({
        "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
        "open": [c.open for c in candles],
        "high": [c.high for c in candles],
        "low": [c.low for c in candles],
        "close": [c.close for c in candles],
        "volume": [c.volume for c in candles],
    })
    strat = MovingAverageCrossover(parameters={"symbol": symbol})
    result = strat.generate_signals(data)
    return result.signals


def _daily_summary_rule(config: dict) -> AlertRule:
    hour = config.get("rules", {}).get("daily_summary", {}).get("hour", 23)
    minute = config.get("rules", {}).get("daily_summary", {}).get("minute", 0)

    def check() -> Alert | None:
        now = datetime.now(timezone.utc)
        if now.hour == hour and now.minute == minute:
            return Alert(
                level="INFO",
                category="SUMMARY",
                title="Daily Summary",
                message=f"CriptoLab monitor running. Time: {now.strftime('%Y-%m-%d %H:%M')} UTC",
            )
        return None

    return AlertRule(name="daily_summary", check_fn=check, interval_seconds=60)


def cmd_monitor(args: argparse.Namespace) -> None:
    alerts_config = _load_alerts_config()
    if not alerts_config.get("enabled", True):
        print("Alerts disabled in settings.yaml")
        return

    manager = build_alert_manager(alerts_config)
    engine = AlertEngine(manager)
    config = load_settings()
    conn = get_connection(config.database.path)

    symbols = args.symbols or ["BTCUSDT"]
    interval = alerts_config.get("check_interval_seconds", 300)

    for symbol in symbols:
        cfg = alerts_config.get("rules", {})
        if cfg.get("price", {}).get("enabled", True):
            engine.add_rule(price_alert_rule(
                symbol=symbol,
                current_price_fn=lambda s=symbol: _get_latest_price(s, conn),
            ))
        if cfg.get("signal", {}).get("enabled", True):
            engine.add_rule(signal_alert_rule(
                symbol=symbol,
                signals_fn=lambda s=symbol: _get_signals(s, conn),
            ))
        if cfg.get("risk", {}).get("enabled", True):
            engine.add_rule(risk_alert_rule(
                symbol="PORTFOLIO",  # We are monitoring overall portfolio drawdown
                drawdown_fn=lambda: _get_current_drawdown(conn),
                max_drawdown=cfg.get("risk", {}).get("max_drawdown_pct", 20.0),
            ))

    engine.add_rule(_daily_summary_rule(alerts_config))

    print(f"Alert monitor started. Checking every {interval}s. Symbols: {symbols}")
    print(f"History: {HISTORY_FILE}")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            triggered = engine.tick()
            if triggered:
                for alert in triggered:
                    print(f"  Triggered: [{alert.category}] {alert.title}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")


def cmd_history(args: argparse.Namespace) -> None:
    manager = build_alert_manager()
    entries = manager.get_history(limit=args.limit)
    if not entries:
        print("No alerts in history.")
        return
    print(f"{'Timestamp':<22} {'Level':<8} {'Category':<10} Title")
    print("-" * 80)
    for e in entries:
        print(f"{e['timestamp']:<22} {e['level']:<8} {e['category']:<10} {e['title']}")


def cmd_clear(args: argparse.Namespace) -> None:
    manager = build_alert_manager()
    manager.clear_history()
    print("Alert history cleared.")


def main() -> None:
    parser = argparse.ArgumentParser(description="CriptoLab Alert Monitor")

    sub = parser.add_subparsers(dest="command", required=True)

    mon = sub.add_parser("monitor", help="Run continuous alert monitoring")
    mon.add_argument("--symbols", nargs="+", default=None, help="Symbols to monitor (default: BTCUSDT)")

    hist = sub.add_parser("history", help="View alert history")
    hist.add_argument("--limit", type=int, default=20, help="Number of entries to show")

    sub.add_parser("clear", help="Clear alert history")

    args = parser.parse_args()

    if args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "history":
        cmd_history(args)
    elif args.command == "clear":
        cmd_clear(args)


if __name__ == "__main__":
    main()
