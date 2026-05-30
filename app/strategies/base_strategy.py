from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class Signal:
    symbol: str
    timestamp: pd.Timestamp
    action: str
    price: float
    reason: str
    confidence: float = 0.5
    risk_score: float = 0.5
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size_pct: Optional[float] = None


@dataclass
class StrategyResult:
    signals: list[Signal] = field(default_factory=list)


class BaseStrategy(ABC):
    def __init__(self, parameters: dict | None = None) -> None:
        self.parameters = parameters or {}

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        ...
