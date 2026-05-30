from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from app.config import load_settings
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.paper_trading.simulator import PaperTradingSimulator
from app.risk.circuit_breakers import CircuitBreakers
from app.risk.risk_manager import RiskManager
from app.strategies import (
    DCADynamic,
    MovingAverageCrossover,
    RSIStrategy,
    RebalanceStrategy,
    TrendFollowing,
)
from app.strategies.base_strategy import Signal

BAR_PROGRESS_EVERY = 500


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run paper trading simulation on historical data")
    parser.add_argument("--symbol", default="BTCUSDT", help="Trading pair")
    parser.add_argument("--interval", default="4h", help="Candle interval")
    parser.add_argument("--strategy", required=True, choices=["ma", "rsi", "trend", "dca", "rebalance"],
                        help="Strategy to trade")
    parser.add_argument("--capital", type=float, default=1000.0, help="Starting capital")
    parser.add_argument("--start-ms", type=int, default=None, help="Start time in ms")
    parser.add_argument("--end-ms", type=int, default=None, help="End time in ms")
    parser.add_argument("--limit", type=int, default=None, help="Max candles to load")
    parser.add_argument("--settings", default="settings.yaml", help="Path to settings YAML")
    parser.add_argument("--export-trades", type=Path, default=None, help="Export trades to JSON file")
    return parser.parse_args()


def _build_strategy(name: str, symbol: str):
    params = {"symbol": symbol}
    strategy_map = {
        "ma": MovingAverageCrossover,
        "rsi": RSIStrategy,
        "trend": TrendFollowing,
        "dca": DCADynamic,
        "rebalance": RebalanceStrategy,
    }
    cls = strategy_map.get(name)
    if cls is None:
        raise ValueError(f"Unknown strategy: {name}")
    return cls(parameters=params)


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


def _build_signal_map(signals: list[Signal]) -> dict[str, Signal]:
    return {str(signal.timestamp): signal for signal in signals}


def _run_simulation(
    data: pd.DataFrame,
    simulator: PaperTradingSimulator,
    signal_map: dict[str, Signal],
    symbol: str,
) -> float:
    print(f"\nRunning paper trading simulation on {len(data)} bars...")
    start_time = time.time()
    for i, (_, row) in enumerate(data.iterrows()):
        ts = row["timestamp"]
        price = float(row["close"])
        simulator.portfolio.update_prices({symbol: price})

        signal = signal_map.get(str(ts))
        if signal and signal.action in ("BUY", "SELL"):
            simulator.process_signal(signal, price)

        if (i + 1) % BAR_PROGRESS_EVERY == 0:
            status = simulator.get_status()
            pct = (i + 1) / len(data) * 100
            print(
                f"  [{pct:5.1f}%] bar {i+1}/{len(data)} | value: ${status['total_value']:.2f} | "
                f"trades: {status['trades_executed']} | dd: {status['drawdown_pct']:.1f}%"
            )

    return time.time() - start_time


def _print_results(
    args: argparse.Namespace,
    data: pd.DataFrame,
    simulator: PaperTradingSimulator,
    elapsed: float,
) -> None:
    status = simulator.get_status()
    print(f"\n{'='*50}")
    print(f"Paper Trading Results - {args.strategy.upper()} on {args.symbol} {args.interval}")
    print(f"{'='*50}")
    print(f"Period:     {data['timestamp'].iloc[0].date()} -> {data['timestamp'].iloc[-1].date()}")
    print(f"Duration:   {len(data)} bars ({elapsed:.1f}s simulation)")
    print(f"Capital:    ${args.capital:.2f} -> ${status['total_value']:.2f}")
    print(f"Return:     {status['total_pnl_pct']:+.2f}%")
    print(f"Drawdown:   {status['drawdown_pct']:.2f}%")
    print(f"Trades:     {status['trades_executed']} executed, {status['trades_rejected']} rejected")
    print(f"Cash:       ${status['cash']:.2f}")
    print(f"Exposure:   {status['exposure_pct']:.1f}%")


def _maybe_export_trades(args: argparse.Namespace, simulator: PaperTradingSimulator) -> None:
    if not args.export_trades:
        return
    trades = simulator.portfolio.get_trade_history()
    with args.export_trades.open("w") as f:
        json.dump(trades, f, indent=2)
    print(f"\nTrades exported to {args.export_trades}")


def _print_snapshot_summary(simulator: PaperTradingSimulator) -> None:
    snapshots = simulator.portfolio.get_snapshots()
    if not snapshots:
        return
    print(f"\nSnapshots: {len(snapshots)}")
    print(f"  First: ${snapshots[0].total_value:.2f} | Last: ${snapshots[-1].total_value:.2f}")
    peak = max(s.total_value for s in snapshots)
    print(f"  Peak:  ${peak:.2f}")


def main() -> None:
    args = parse_args()
    config = load_settings(args.settings)
    conn = get_connection(config.database.path)

    print(f"Loading {args.symbol} {args.interval} data...")
    candles = get_candles(
        connection=conn,
        symbol=args.symbol,
        interval=args.interval,
        start_time_ms=args.start_ms,
        end_time_ms=args.end_ms,
        limit=args.limit,
    )

    if len(candles) < 50:
        raise RuntimeError(f"Not enough data ({len(candles)} candles). Download first.")

    data = _to_dataframe(candles)
    print(f"Loaded {len(data)} candles ({data['timestamp'].iloc[0].date()} -> {data['timestamp'].iloc[-1].date()})")

    strategy = _build_strategy(args.strategy, args.symbol)

    circuit_breakers = CircuitBreakers(
        max_daily_loss_pct=3.0,
        max_weekly_loss_pct=7.0,
        max_consecutive_losses=5,
        max_trades_per_day=10,
        kill_switch=False,
    )

    risk_manager = RiskManager(
        circuit_breakers=circuit_breakers,
    )

    simulator = PaperTradingSimulator(
        strategy=strategy,
        risk_manager=risk_manager,
        initial_capital=args.capital,
        symbol=args.symbol,
    )

    signals = strategy.generate_signals(data)
    signal_map = _build_signal_map(signals.signals)
    print(f"Strategy generated {len(signal_map)} signals")
    elapsed = _run_simulation(data, simulator, signal_map, args.symbol)
    _print_results(args, data, simulator, elapsed)
    _maybe_export_trades(args, simulator)
    _print_snapshot_summary(simulator)


if __name__ == "__main__":
    main()
