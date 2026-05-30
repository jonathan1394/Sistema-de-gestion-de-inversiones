"""Backtesting package exports for engine, metrics, and reports."""

from app.backtesting.engine import BacktestEngine, BacktestResult, TradeRecord
from app.backtesting.metrics import BacktestMetrics, compute_metrics
from app.backtesting.reports import (
    export_equity_csv,
    export_metrics_json,
    export_trades_csv,
    generate_report,
)

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "TradeRecord",
    "BacktestMetrics",
    "compute_metrics",
    "generate_report",
    "export_metrics_json",
    "export_trades_csv",
    "export_equity_csv",
]
