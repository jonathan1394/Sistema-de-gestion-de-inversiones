"""Base classes and data models for trading strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class Signal:
    """Represents a single buy/sell signal emitted by a strategy."""

    symbol: str
    timestamp: pd.Timestamp
    action: str
    price: float
    reason: str
    direction: str = "long"
    confidence: float = 0.5
    risk_score: float = 0.5
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_pct: Optional[float] = None


@dataclass
class StrategyResult:
    """Container for signals produced by a strategy run."""

    signals: list[Signal] = field(default_factory=list)
    warning: str = ""


class BaseStrategy(ABC):
    """Abstract base class that all trading strategies must implement."""

    def __init__(self, parameters: dict | None = None) -> None:
        self.parameters = parameters or {}
        self.stop_loss_pct = float(self.parameters.get("stop_loss_pct", 0.02))
        self.take_profit_pct = float(self.parameters.get("take_profit_pct", 0.04))
        self.min_required_bars = int(self.parameters.get("min_required_bars", 0))
        self.confidence = float(self.parameters.get("confidence", 0.5))
        self.risk_score = float(self.parameters.get("risk_score", 0.5))

    def _check_min_bars(self, data: pd.DataFrame) -> StrategyResult | None:
        if len(data) < self.min_required_bars:
            return StrategyResult(
                signals=[],
                warning=f"Need at least {self.min_required_bars} bars, got {len(data)}",
            )
        return None

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """Generate trading signals from OHLCV data."""
        ...
