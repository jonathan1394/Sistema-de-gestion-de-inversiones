"""Backtest reporting helpers for text and file exports."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from app.backtesting.engine import BacktestResult
from app.backtesting.metrics import compute_metrics

logger = logging.getLogger(__name__)

def generate_report(result: BacktestResult) -> str:
    """Generate human-readable backtest report text."""
    metrics = compute_metrics(result)

    lines = []
    lines.append("=" * 60)
    lines.append(f"BACKTEST REPORT — {result.strategy_name}")
    lines.append("=" * 60)
    lines.append(f"Symbol:          {result.symbol}")
    lines.append(f"Interval:        {result.interval}")
    lines.append(f"Initial Capital: ${result.initial_capital:,.2f}")
    lines.append(f"Final Capital:   ${result.final_capital:,.2f}")
    lines.append(f"Total Fees:      ${result.total_fees:,.2f}")
    lines.append("")

    lines.append("--- Performance ---")
    lines.append(f"ROI:              {metrics.roi_pct:+.2f}%")
    lines.append(f"CAGR:             {metrics.cagr_pct:+.2f}%")
    lines.append(f"Max Drawdown:     {metrics.max_drawdown_pct:.2f}%")
    lines.append(f"Sharpe Ratio:     {metrics.sharpe_ratio:.2f}")
    lines.append(f"Sortino Ratio:    {metrics.sortino_ratio:.2f}")
    lines.append(f"Time in Market:   {metrics.time_in_market_pct:.1f}%")
    lines.append("")

    lines.append("--- Trade Statistics ---")
    lines.append(f"Total Trades:     {metrics.total_trades}")
    lines.append(f"Winning Trades:   {metrics.winning_trades}")
    lines.append(f"Losing Trades:    {metrics.losing_trades}")
    lines.append(f"Win Rate:         {metrics.win_rate:.1f}%")
    lines.append(f"Profit Factor:    {metrics.profit_factor:.2f}")
    lines.append(f"Expectancy:       {metrics.expectancy:+.2f}%")
    lines.append("")

    lines.append("--- Average Trade ---")
    lines.append(f"Avg Win:          {metrics.avg_win_pct:+.2f}%")
    lines.append(f"Avg Loss:         {metrics.avg_loss_pct:+.2f}%")
    lines.append(f"Payoff Ratio:     {metrics.payoff_ratio:.2f}")
    lines.append(f"Avg Hold (bars):  {metrics.avg_hold_bars:.1f}")
    lines.append("")

    lines.append("--- Extremes ---")
    lines.append(f"Largest Win:      {metrics.largest_win_pct:+.2f}%")
    lines.append(f"Largest Loss:     {metrics.largest_loss_pct:+.2f}%")
    lines.append(f"Consecutive Wins: {metrics.consecutive_wins}")
    lines.append(f"Consecutive Losses: {metrics.consecutive_losses}")
    lines.append("")

    if result.parameters:
        lines.append("--- Parameters ---")
        for key, value in result.parameters.items():
            lines.append(f"  {key}: {value}")
        lines.append("")

    return "\n".join(lines)


def export_metrics_json(result: BacktestResult, output_path: str | Path) -> Path:
    """Export result and metrics payload to JSON file."""
    metrics = compute_metrics(result)
    payload = {
        "symbol": result.symbol,
        "interval": result.interval,
        "strategy_name": result.strategy_name,
        "parameters": result.parameters,
        "initial_capital": result.initial_capital,
        "final_capital": result.final_capital,
        "total_fees": result.total_fees,
        "metrics": metrics.__dict__,
    }

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return destination


def export_trades_csv(result: BacktestResult, output_path: str | Path) -> Path:
    """Export closed trades to CSV file."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "symbol",
                "side",
                "entry_time",
                "exit_time",
                "entry_price",
                "exit_price",
                "quantity",
                "fees",
                "pnl",
                "pnl_pct",
                "reason_entry",
                "reason_exit",
                "hold_bars",
                "stop_loss",
                "take_profit",
            ],
        )
        writer.writeheader()
        for trade in result.trades:
            writer.writerow(
                {
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "entry_time": trade.entry_time.isoformat(),
                    "exit_time": trade.exit_time.isoformat() if trade.exit_time else "",
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "quantity": trade.quantity,
                    "fees": trade.fees,
                    "pnl": trade.pnl,
                    "pnl_pct": trade.pnl_pct,
                    "reason_entry": trade.reason_entry,
                    "reason_exit": trade.reason_exit,
                    "hold_bars": trade.hold_bars,
                    "stop_loss": trade.stop_loss,
                    "take_profit": trade.take_profit,
                }
            )

    return destination


def export_equity_csv(result: BacktestResult, output_path: str | Path) -> Path:
    """Export equity curve values to CSV file."""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "equity"])
        writer.writeheader()
        for timestamp, equity_value in result.equity_curve.items():
            writer.writerow(
                {
                    "timestamp": timestamp.isoformat(),
                    "equity": float(equity_value),
                }
            )

    return destination
