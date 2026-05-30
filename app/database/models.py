"""Data models for CriptoLab.

Centraliza los modelos de datos usados en todo el sistema.
"""

from app.data.market_data import Candle, DownloadResult
from app.strategies.base_strategy import Signal, StrategyResult
from app.backtesting.engine import TradeRecord, BacktestResult

__all__ = [
    "Candle",
    "DownloadResult",
    "Signal",
    "StrategyResult",
    "TradeRecord",
    "BacktestResult",
]
