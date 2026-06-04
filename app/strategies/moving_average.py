"""Moving Average Crossover strategy using fast/slow EMA signals."""

from __future__ import annotations

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult


class MovingAverageCrossover(BaseStrategy):
    """Buy when fast EMA crosses above slow EMA, sell on the reverse."""

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """Generate BUY/SELL signals on fast EMA crossing slow EMA."""
        fast_period = self.parameters.get("fast_period", 20)
        slow_period = self.parameters.get("slow_period", 50)
        symbol = self.parameters.get("symbol", "UNKNOWN")
        self.min_required_bars = int(self.parameters.get("min_required_bars", slow_period + 1))
        not_enough = self._check_min_bars(data)
        if not_enough is not None:
            return not_enough

        df = data.copy()
        df["ema_fast"] = df["close"].ewm(span=fast_period, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=slow_period, adjust=False).mean()
        df["prev_fast"] = df["ema_fast"].shift(1)
        df["prev_slow"] = df["ema_slow"].shift(1)

        entry = (df["prev_fast"] <= df["prev_slow"]) & (df["ema_fast"] > df["ema_slow"])
        exit_ = (df["prev_fast"] >= df["prev_slow"]) & (df["ema_fast"] < df["ema_slow"])

        net_position = (entry.cumsum() - exit_.cumsum()).clip(0, 1)
        prev_position = net_position.shift(1).fillna(0)

        buy_idx = df.index[entry & (prev_position == 0)]
        sell_idx = df.index[exit_ & (prev_position == 1)]

        signals: list[Signal] = []
        for idx in buy_idx:
            price = df.loc[idx, "close"]
            signals.append(
                Signal(
                    symbol=symbol,
                    timestamp=pd.Timestamp(idx),
                    price=price,
                    action="BUY",
                    reason=f"EMA{fast_period} crossed above EMA{slow_period}",
                    confidence=self.confidence,
                    risk_score=self.risk_score,
                    stop_loss=price * (1 - self.stop_loss_pct),
                    take_profit=price * (1 + self.take_profit_pct),
                )
            )
        for idx in sell_idx:
            signals.append(
                Signal(
                    symbol=symbol,
                    timestamp=pd.Timestamp(idx),
                    price=df.loc[idx, "close"],
                    action="SELL",
                    reason=f"EMA{fast_period} crossed below EMA{slow_period}",
                    confidence=self.confidence,
                    risk_score=self.risk_score,
                )
            )

        return StrategyResult(signals=signals)
