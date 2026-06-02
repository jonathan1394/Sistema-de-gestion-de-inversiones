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
    "DecisionLog",
]


class DecisionLog:
    """Decision log record for audit trail.

    This is a plain class representing a row from the decision_log table.
    It does not contain any SQLAlchemy or ORM mapping; it is used for
    type hints and documentation only.
    """

    def __init__(
        self,
        decision_id: str,
        decision_type: str,
        timestamp: str,
        symbol: str | None,
        strategy_name: str | None,
        timeframe: str | None,
        mode: str,
        approved: bool,
        reason: str,
        input_json: str | dict,
        output_json: str | dict,
        policy_version: str | None = None,
        strategy_version: str | None = None,
    ) -> None:
        self.decision_id = decision_id
        self.decision_type = decision_type
        self.timestamp = timestamp
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.timeframe = timeframe
        self.mode = mode
        self.approved = approved
        self.reason = reason
        self.input_json = input_json
        self.output_json = output_json
        self.policy_version = policy_version
        self.strategy_version = strategy_version
