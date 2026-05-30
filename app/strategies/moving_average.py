from __future__ import annotations

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult


class MovingAverageCrossover(BaseStrategy):
    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        fast_period = self.parameters.get("fast_period", 20)
        slow_period = self.parameters.get("slow_period", 50)
        symbol = self.parameters.get("symbol", "UNKNOWN")

        df = data.copy()
        df["ema_fast"] = df["close"].ewm(span=fast_period, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=slow_period, adjust=False).mean()
        df["prev_fast"] = df["ema_fast"].shift(1)
        df["prev_slow"] = df["ema_slow"].shift(1)

        signals: list[Signal] = []
        in_position = False

        for idx, row in df.iterrows():
            timestamp = idx if isinstance(idx, pd.Timestamp) else pd.Timestamp(row.get("timestamp", idx))
            price = row["close"]

            crossover_buy = row["prev_fast"] <= row["prev_slow"] and row["ema_fast"] > row["ema_slow"]
            crossover_sell = row["prev_fast"] >= row["prev_slow"] and row["ema_fast"] < row["ema_slow"]

            if crossover_buy and not in_position:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    action="BUY",
                    price=price,
                    reason=f"EMA{fast_period} crossed above EMA{slow_period}",
                    confidence=0.6,
                    risk_score=0.4,
                ))
                in_position = True

            elif crossover_sell and in_position:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    action="SELL",
                    price=price,
                    reason=f"EMA{fast_period} crossed below EMA{slow_period}",
                    confidence=0.6,
                    risk_score=0.4,
                ))
                in_position = False

        return StrategyResult(signals=signals)
