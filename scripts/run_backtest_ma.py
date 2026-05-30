from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from app.backtesting.engine import BacktestEngine
from app.backtesting.reports import (
    export_equity_csv,
    export_metrics_json,
    export_trades_csv,
    generate_report,
)
from app.config import load_settings
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.strategies.moving_average import MovingAverageCrossover


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run moving average backtest from SQLite data")
    parser.add_argument("--symbol", required=True, help="Symbol like BTCUSDT")
    parser.add_argument("--interval", required=True, help="Interval like 1h, 4h, 1d")
    parser.add_argument("--start-ms", type=int, default=None, help="Start time in ms")
    parser.add_argument("--end-ms", type=int, default=None, help="End time in ms")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to read from DB")
    parser.add_argument("--fast", type=int, default=20, help="Fast EMA period")
    parser.add_argument("--slow", type=int, default=50, help="Slow EMA period")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital")
    parser.add_argument("--commission", type=float, default=0.001, help="Commission percent decimal")
    parser.add_argument("--slippage", type=float, default=0.001, help="Slippage percent decimal")
    parser.add_argument(
        "--export-dir",
        default=None,
        help="Directory to export metrics.json, trades.csv and equity_curve.csv",
    )
    parser.add_argument("--settings", default="settings.yaml", help="Path to settings YAML")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_settings(args.settings)
    conn = get_connection(config.database.path)

    candles = get_candles(
        connection=conn,
        symbol=args.symbol,
        interval=args.interval,
        start_time_ms=args.start_ms,
        end_time_ms=args.end_ms,
        limit=args.limit,
    )
    if len(candles) < max(args.fast, args.slow) + 5:
        raise RuntimeError("Not enough candles for selected moving average periods")

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

    strategy = MovingAverageCrossover(
        parameters={
            "symbol": args.symbol.upper(),
            "fast_period": args.fast,
            "slow_period": args.slow,
        }
    )
    engine = BacktestEngine(
        strategy=strategy,
        data=data,
        initial_capital=args.capital,
        commission_pct=args.commission,
        slippage_pct=args.slippage,
        symbol=args.symbol.upper(),
        interval=args.interval,
    )
    result = engine.run()
    print(generate_report(result))

    if args.export_dir:
        export_dir = Path(args.export_dir)
        metrics_path = export_metrics_json(result, export_dir / "metrics.json")
        trades_path = export_trades_csv(result, export_dir / "trades.csv")
        equity_path = export_equity_csv(result, export_dir / "equity_curve.csv")
        print("")
        print("Exports:")
        print(f"- {metrics_path}")
        print(f"- {trades_path}")
        print(f"- {equity_path}")


if __name__ == "__main__":
    main()
