from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from loguru import logger

from app.ai.journal_analyzer import generate_journal_report
from app.ai.market_summary import format_summary, generate_market_summary
from app.ai.signal_explainer import explain_signal
from app.config import load_settings
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.logging_setup import setup_logging
from app.strategies.moving_average import MovingAverageCrossover
from app.strategies.rsi_strategy import RSIStrategy
from app.strategies.trend_following import TrendFollowing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Analysis Tools for Crypto Lab")

    sub = parser.add_subparsers(dest="command", required=True)

    market_parser = sub.add_parser("market", help="Generate market summary")
    market_parser.add_argument("--symbol", default="BTCUSDT", help="Trading pair symbol")
    market_parser.add_argument("--interval", default="4h", help="Candle interval")
    market_parser.add_argument("--period", default="7", help="Days of data to analyze")
    market_parser.add_argument("--settings", default="settings.yaml", help="Path to settings YAML")

    signal_parser = sub.add_parser("signals", help="Explain signals from a strategy")
    signal_parser.add_argument("--symbol", default="BTCUSDT", help="Trading pair symbol")
    signal_parser.add_argument("--interval", default="4h", help="Candle interval")
    signal_parser.add_argument(
        "--strategy",
        default="ma",
        choices=["ma", "rsi", "trend"],
        help="Strategy to generate signals",
    )
    signal_parser.add_argument("--limit", type=int, default=200, help="Candles to load")
    signal_parser.add_argument("--settings", default="settings.yaml", help="Path to settings YAML")

    journal_parser = sub.add_parser("journal", help="Analyze trading journal")
    journal_parser.add_argument("--file", required=True, type=Path, help="Path to trades JSON file")

    return parser.parse_args()


def cmd_market(args: argparse.Namespace) -> None:
    config = load_settings(args.settings)
    conn = get_connection(config.database.path)

    candles = get_candles(
        connection=conn,
        symbol=args.symbol,
        interval=args.interval,
        limit=int(args.period) * 100,
        desc=True,
    )

    if len(candles) < 10:
        logger.info("Not enough data for %s (%s). Download first.", args.symbol, args.interval)
        return

    data = pd.DataFrame(
        {
            "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }
    )

    summary = generate_market_summary(data, symbol=args.symbol, period=args.interval)
    print(format_summary(summary))


def cmd_signals(args: argparse.Namespace) -> None:
    config = load_settings(args.settings)
    conn = get_connection(config.database.path)

    candles = get_candles(
        connection=conn,
        symbol=args.symbol,
        interval=args.interval,
        limit=args.limit,
        desc=True,
    )

    if len(candles) < 50:
        logger.info("Not enough data (got %d, need 50+).", len(candles))
        return

    data = pd.DataFrame(
        {
            "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }
    )

    strategy_map = {
        "ma": MovingAverageCrossover,
        "rsi": RSIStrategy,
        "trend": TrendFollowing,
    }
    cls = strategy_map[args.strategy]
    strategy = cls(parameters={"symbol": args.symbol})

    result = strategy.generate_signals(data)

    if not result.signals:
        logger.info("No signals generated.")
        return

    explanations = [explain_signal(s, data) for s in result.signals[-5:]]

    for exp in explanations:
        print(f"[{exp.signal.timestamp}] {exp.explanation}")
        print(f"  Strength: {exp.strength} | Confidence: {exp.signal.confidence:.0%}")
        if exp.context:
            ctx = " | ".join(f"{k}: {v}" for k, v in exp.context.items())
            print(f"  Context: {ctx}")
        if exp.risk_note:
            print(f"  ⚠ {exp.risk_note}")
        print()


def cmd_journal(args: argparse.Namespace) -> None:
    if not args.file.exists():
        logger.info("File not found: %s", args.file)
        return

    with args.file.open("r") as f:
        trades = json.load(f)

    if isinstance(trades, dict):
        trades = [trades]

    report = generate_journal_report(trades)

    print(report.summary)
    print()
    a = report.trade_analysis
    print(f"Total trades: {a.total_trades}")
    print(f"Win rate: {a.win_rate:.1f}%")
    print(f"Profit factor: {a.profit_factor:.2f}")
    print(f"Avg win: {a.avg_win:+.2f}% | Avg loss: {a.avg_loss:+.2f}%")
    print(f"Largest win: {a.largest_win:+.2f}% | Largest loss: {a.largest_loss:+.2f}%")
    print(f"Consecutive wins: {a.consecutive_wins} | Consecutive losses: {a.consecutive_losses}")
    print(f"Avg hold: {a.avg_hold_time:.1f} bars")

    if report.behavior.details:
        print("\nBehavior flags:")
        for d in report.behavior.details:
            print(f"  ⚠ {d}")

    print(f"\nWeakness: {report.insight.weakness}")
    print(f"Suggestion: {report.insight.suggestion}")


def main() -> None:
    args = parse_args()
    setup_logging()

    if args.command == "market":
        cmd_market(args)
    elif args.command == "signals":
        cmd_signals(args)
    elif args.command == "journal":
        cmd_journal(args)


if __name__ == "__main__":
    main()
