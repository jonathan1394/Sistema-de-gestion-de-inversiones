from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from app.backtesting.comparator import (
    DEFAULT_STRATEGIES,
    compare_across_assets,
    compute_weighted_score,
)
from app.config import load_settings
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare multiple strategies across assets and timeframes"
    )
    parser.add_argument(
        "--symbols",
        default="BTCUSDT,ETHUSDT,SOLUSDT",
        help="Comma-separated list of symbols (default: BTCUSDT,ETHUSDT,SOLUSDT)",
    )
    parser.add_argument(
        "--intervals",
        default="1h,4h,1d",
        help="Comma-separated list of intervals (default: 1h,4h,1d)",
    )
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital")
    parser.add_argument("--commission", type=float, default=0.001, help="Commission pct (decimal)")
    parser.add_argument("--slippage", type=float, default=0.001, help="Slippage pct (decimal)")
    parser.add_argument("--limit", type=int, default=500, help="Max candles per asset/TF")
    parser.add_argument("--min-trades", type=int, default=0, help="Minimum trades filter")
    parser.add_argument("--min-sharpe", type=float, default=0.0, help="Minimum Sharpe filter")
    parser.add_argument(
        "--export-json", type=Path, default=None, help="Export ranking to JSON file"
    )
    parser.add_argument(
        "--export-csv", type=Path, default=None, help="Export ranking to CSV file"
    )
    parser.add_argument(
        "--settings", default="settings.yaml", help="Path to settings YAML"
    )
    parser.add_argument(
        "--w-sharpe", type=float, default=1.5, help="Weight for Sharpe in scoring"
    )
    parser.add_argument(
        "--w-drawdown", type=float, default=2.0, help="Weight for drawdown in scoring"
    )
    parser.add_argument(
        "--w-profit-factor", type=float, default=1.0, help="Weight for profit factor in scoring"
    )
    return parser.parse_args()


def load_data(
    conn,
    symbol: str,
    interval: str,
    limit: int = 500,
) -> pd.DataFrame | None:
    candles = get_candles(
        connection=conn,
        symbol=symbol,
        interval=interval,
        limit=limit,
        desc=True,
    )
    if not candles or len(candles) < 50:
        return None

    return pd.DataFrame({
        "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
        "open": [c.open for c in candles],
        "high": [c.high for c in candles],
        "low": [c.low for c in candles],
        "close": [c.close for c in candles],
        "volume": [c.volume for c in candles],
    })


def main() -> None:
    args = parse_args()
    config = load_settings(args.settings)
    setup_logging()
    conn = get_connection(config.database.path)

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    intervals = [s.strip() for s in args.intervals.split(",")]

    data_by_asset: dict[str, dict[str, pd.DataFrame]] = {}

    logger.info("Loading data for %d symbols x %d timeframes...", len(symbols), len(intervals))
    for symbol in symbols:
        data_by_asset[symbol] = {}
        for interval in intervals:
            df = load_data(conn, symbol, interval, limit=args.limit)
            if df is not None:
                data_by_asset[symbol][interval] = df
                logger.info("  %s %s: %d candles", symbol, interval, len(df))
            else:
                logger.info("  %s %s: insufficient data (skipped)", symbol, interval)

    if not any(data_by_asset.values()):
        logger.error("No data available. Download historical data first.")
        return

    logger.info("Running %d strategies across all assets...", len(DEFAULT_STRATEGIES))
    ranking = compare_across_assets(
        data_by_asset=data_by_asset,
        initial_capital=args.capital,
        commission_pct=args.commission,
        slippage_pct=args.slippage,
        min_trades=args.min_trades,
        min_sharpe=args.min_sharpe,
    )

    weights = {
        "sharpe": args.w_sharpe,
        "drawdown": args.w_drawdown,
        "profit_factor": args.w_profit_factor,
    }

    print(f"\n=== RANKING ({len(ranking.entries)} entries) ===")
    print(
        f"{'Rank':<5} {'Symbol':<10} {'TF':<5} {'Strategy':<20} "
        f"{'Sharpe':<8} {'DD%':<8} {'PF':<8} {'ROI%':<8} {'Trades':<7} {'Score':<8}"
    )
    print("-" * 90)

    for i, entry in enumerate(ranking.entries, 1):
        score = compute_weighted_score(entry, weights)
        valid_mark = "✓" if entry["passed_validation"] else " "
        print(
            f"{i:<5} {entry['symbol']:<10} {entry['interval']:<5} "
            f"{entry['strategy']:<20} {entry['sharpe_ratio']:<8} "
            f"{entry['max_drawdown_pct']:<8} {entry['profit_factor']:<8} "
            f"{entry['roi_pct']:<8} {entry['total_trades']:<7} {score:<8} {valid_mark}"
        )

    if args.export_json:
        args.export_json.parent.mkdir(parents=True, exist_ok=True)
        with args.export_json.open("w") as f:
            json.dump(
                {
                    "ranking": ranking.entries,
                    "filters": {
                        "min_trades": args.min_trades,
                        "min_sharpe": args.min_sharpe,
                    },
                    "weights": weights,
                },
                f,
                indent=2,
            )
        logger.info("Ranking exported to %s", args.export_json)

    if args.export_csv:
        args.export_csv.parent.mkdir(parents=True, exist_ok=True)
        df = ranking.to_dataframe()
        df.to_csv(args.export_csv, index=False)
        logger.info("Ranking exported to %s", args.export_csv)


if __name__ == "__main__":
    main()
