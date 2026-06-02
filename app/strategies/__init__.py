"""Trading strategies package with built-in signal generators."""

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult
from app.strategies.dca_dynamic import DCADynamic
from app.strategies.moving_average import MovingAverageCrossover
from app.strategies.rebalance import RebalanceStrategy
from app.strategies.rsi_strategy import RSIStrategy
from app.strategies.trend_following import TrendFollowing

__all__ = [
    "BaseStrategy",
    "Signal",
    "StrategyResult",
    "MovingAverageCrossover",
    "RSIStrategy",
    "TrendFollowing",
    "DCADynamic",
    "RebalanceStrategy",
]
