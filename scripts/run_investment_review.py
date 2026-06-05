#!/usr/bin/env python3
"""Run the official daily investment review routine."""

from __future__ import annotations

import argparse

from app.config import load_settings
from app.database.connection import get_connection
from app.evaluation.review import build_investment_review


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the investment review routine")
    parser.add_argument("--symbol", help="Single symbol to review. Defaults to all configured symbols")
    parser.add_argument("--interval", default="1d", help="Prospecting interval to evaluate")
    parser.add_argument("--backtest-interval", default="4h", help="Interval for comparative backtest")
    parser.add_argument("--backtest-limit", type=int, default=500, help="Candles used by backtest compare")
    parser.add_argument("--amount", type=float, default=50.0, help="Suggested amount in USDT")
    parser.add_argument("--settings", default="settings.yaml", help="Path to settings YAML")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings(args.settings)
    symbols = [args.symbol.upper()] if args.symbol else list(settings.symbols)
    conn = get_connection(settings.database.path)

    print("Official Investment Review")
    print("=" * 80)
    print(f"Universe: {', '.join(settings.symbols)}")
    print(f"Timeframes: {', '.join(settings.timeframes)}")
    print(
        "Promotion rules: "
        f"score>={settings.prospecting.get('recommendation', {}).get('invertir_threshold', 0.75):.2f}, "
        f"confluence>={settings.prospecting.get('recommendation', {}).get('min_confluence_for_invertir', 2)}, "
        f"trades>={settings.backtesting.min_trades_for_validation}, "
        f"profit_factor>{settings.backtesting.min_profit_factor}, "
        f"sharpe>{settings.backtesting.min_sharpe_ratio}"
    )
    print()

    for symbol in symbols:
        review = build_investment_review(
            settings,
            conn,
            symbol=symbol,
            interval=args.interval,
            backtest_interval=args.backtest_interval,
            backtest_limit=args.backtest_limit,
            suggested_amount_usdt=args.amount,
        )
        protocol = review["protocol"]
        ranking = review["ranking"] or {}
        risk = review["risk"] or {}

        print(f"[{symbol}] status={protocol['status']}")
        print(
            f"  recommendation={ranking.get('recommendation', 'N/A')} "
            f"score={ranking.get('score', 0):.4f} confluence={ranking.get('confluence', 'N/A')}"
        )
        print(
            f"  backtest_best={review['backtest'].get('best_strategy') or 'N/A'} "
            f"risk_approved={risk.get('approved', False)}"
        )
        for row in review["data_health"]:
            print(
                f"  data {row['interval']}: status={row['status']} candles={row['count']} age_min={row['age_minutes']}"
            )
        print("  checks:")
        for name, passed in protocol["checks"].items():
            print(f"    - {name}: {'OK' if passed else 'BLOCKED'}")
        print()


if __name__ == "__main__":
    main()
