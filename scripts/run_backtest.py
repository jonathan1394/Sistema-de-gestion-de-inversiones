from __future__ import annotations

import argparse
import json

import pandas as pd

from app.backtesting import BacktestEngine, compute_metrics, generate_report
from app.config import load_settings
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.logging_setup import setup_logging
from app.strategies import (
    DCADynamic,
    MovingAverageCrossover,
    RebalanceStrategy,
    RSIStrategy,
    TrendFollowing,
)


def _build_strategy(name: str, params: dict, symbol: str):
    strategy_map = {
        "ma": MovingAverageCrossover,
        "rsi": RSIStrategy,
        "trend": TrendFollowing,
        "dca": DCADynamic,
        "rebalance": RebalanceStrategy,
    }
    cls = strategy_map.get(name)
    if cls is None:
        raise ValueError(f"Unknown strategy: {name}. Options: {', '.join(strategy_map)}")
    params["symbol"] = symbol
    return cls(parameters=params)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run backtest from SQLite data")
    parser.add_argument("--symbol", required=True, help="Symbol like BTCUSDT")
    parser.add_argument("--interval", required=True, help="Interval like 1h, 4h, 1d")
    parser.add_argument(
        "--strategy",
        required=True,
        choices=["ma", "rsi", "trend", "dca", "rebalance"],
        help="Strategy to backtest",
    )
    parser.add_argument("--start-ms", type=int, default=None, help="Start time in ms")
    parser.add_argument("--end-ms", type=int, default=None, help="End time in ms")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to read from DB")
    parser.add_argument("--capital", type=float, default=1000.0, help="Initial capital")
    parser.add_argument("--commission", type=float, default=0.001, help="Commission as decimal")
    parser.add_argument("--slippage", type=float, default=0.001, help="Slippage as decimal")
    parser.add_argument(
        "--output", default=None, choices=["report", "json", "trades"], help="Output format"
    )
    parser.add_argument("--settings", default="settings.yaml", help="Path to settings YAML")

    parser.add_argument("--ma-fast", type=int, default=20, help="MA fast period")
    parser.add_argument("--ma-slow", type=int, default=50, help="MA slow period")
    parser.add_argument("--rsi-period", type=int, default=14, help="RSI period")
    parser.add_argument("--rsi-oversold", type=int, default=30, help="RSI oversold threshold")
    parser.add_argument("--rsi-overbought", type=int, default=70, help="RSI overbought threshold")
    parser.add_argument("--trend-ema-long", type=int, default=200, help="Trend EMA long")
    parser.add_argument("--dca-base", type=float, default=100.0, help="DCA base amount")
    parser.add_argument("--dca-interval", type=int, default=7, help="DCA interval in days")
    parser.add_argument("--rebalance-target", type=float, default=0.5, help="Rebalance target pct")
    parser.add_argument(
        "--rebalance-threshold", type=float, default=0.05, help="Rebalance threshold"
    )
    return parser.parse_args()


def _strategy_params(args: argparse.Namespace) -> dict:
    mapping = {
        "ma": {
            "fast_period": args.ma_fast,
            "slow_period": args.ma_slow,
        },
        "rsi": {
            "rsi_period": args.rsi_period,
            "oversold": args.rsi_oversold,
            "overbought": args.rsi_overbought,
        },
        "trend": {
            "ema_long": args.trend_ema_long,
            "ema_fast": getattr(args, "ema_fast", 20),
            "ema_slow": getattr(args, "ema_slow", 50),
        },
        "dca": {
            "base_investment": args.dca_base,
            "interval_days": args.dca_interval,
        },
        "rebalance": {
            "target_pct": args.rebalance_target,
            "rebalance_threshold": args.rebalance_threshold,
        },
    }
    return mapping.get(args.strategy, {})


def _to_dataframe(candles: list) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }
    )


def _build_json_output(result, metrics) -> dict:
    return {
        "strategy": result.strategy_name,
        "symbol": result.symbol,
        "interval": result.interval,
        "initial_capital": result.initial_capital,
        "final_capital": round(result.final_capital, 2),
        "total_fees": round(result.total_fees, 2),
        "total_trades": metrics.total_trades,
        "roi_pct": round(metrics.roi_pct, 2),
        "cagr_pct": round(metrics.cagr_pct, 2),
        "max_drawdown_pct": round(metrics.max_drawdown_pct, 2),
        "sharpe_ratio": round(metrics.sharpe_ratio, 2),
        "sortino_ratio": round(metrics.sortino_ratio, 2),
        "win_rate": round(metrics.win_rate, 2),
        "profit_factor": round(metrics.profit_factor, 2),
        "expectancy": round(metrics.expectancy, 2),
    }


def _build_trades_output(result) -> list[dict]:
    return [
        {
            "entry_time": str(t.entry_time),
            "exit_time": str(t.exit_time),
            "entry_price": round(t.entry_price, 2),
            "exit_price": round(t.exit_price, 2) if t.exit_price else None,
            "quantity": round(t.quantity, 6),
            "pnl": round(t.pnl, 2),
            "pnl_pct": round(t.pnl_pct * 100, 2),
            "reason_entry": t.reason_entry,
            "reason_exit": t.reason_exit,
            "hold_bars": t.hold_bars,
        }
        for t in result.trades
    ]


def _print_output(output: str, result, metrics) -> None:
    if output == "json":
        print(json.dumps(_build_json_output(result, metrics), indent=2))
        return
    if output == "trades":
        print(json.dumps(_build_trades_output(result), indent=2))
        return
    print(generate_report(result))


def main() -> None:
    args = parse_args()
    config = load_settings(args.settings)
    setup_logging()
    conn = get_connection(config.database.path)

    candles = get_candles(
        connection=conn,
        symbol=args.symbol,
        interval=args.interval,
        start_time_ms=args.start_ms,
        end_time_ms=args.end_ms,
        limit=args.limit,
    )

    if len(candles) < 50:
        raise RuntimeError(
            f"Only {len(candles)} candles found. Download data first with scripts/download_historical.py"
        )

    data = _to_dataframe(candles)

    params = _strategy_params(args)
    strategy = _build_strategy(args.strategy, params, args.symbol)

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
    metrics = compute_metrics(result)

    output = args.output or "report"

    _print_output(output, result, metrics)


if __name__ == "__main__":
    main()
