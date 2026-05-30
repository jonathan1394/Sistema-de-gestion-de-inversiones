from __future__ import annotations

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult


class DCADynamic(BaseStrategy):
    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        base_investment = self.parameters.get("base_investment", 100.0)
        interval_days = self.parameters.get("interval_days", 7)
        drop_threshold_1 = self.parameters.get("drop_threshold_1", 0.10)
        drop_threshold_2 = self.parameters.get("drop_threshold_2", 0.20)
        increase_1 = self.parameters.get("increase_1", 1.5)
        increase_2 = self.parameters.get("increase_2", 2.0)
        ema_period = self.parameters.get("ema_period", 200)
        reduce_multiplier = self.parameters.get("reduce_multiplier", 0.5)
        symbol = self.parameters.get("symbol", "UNKNOWN")

        df = data.copy()
        df["ema_long"] = df["close"].ewm(span=ema_period, adjust=False).mean()
        df["max_recent"] = df["close"].rolling(window=30).max()

        signals: list[Signal] = []
        last_buy_idx = -interval_days

        for idx, row in df.iterrows():
            timestamp = idx if isinstance(idx, pd.Timestamp) else pd.Timestamp(row.get("timestamp", idx))
            price = row["close"]

            if len(df) < 1:
                continue

            position = df.index.get_loc(idx)
            if position < last_buy_idx + interval_days:
                continue

            if pd.isna(row["max_recent"]) or row["max_recent"] == 0:
                continue

            drop_from_high = (row["max_recent"] - price) / row["max_recent"]
            below_ema = price < row["ema_long"] if not pd.isna(row["ema_long"]) else False

            if drop_from_high >= drop_threshold_2:
                multiplier = increase_2
            elif drop_from_high >= drop_threshold_1:
                multiplier = increase_1
            else:
                multiplier = 1.0

            if below_ema:
                multiplier *= reduce_multiplier

            position_size_pct = 0.1 * multiplier
            if below_ema:
                position_size_pct *= 0.5

            signals.append(Signal(
                symbol=symbol,
                timestamp=timestamp,
                action="BUY",
                price=price,
                reason=f"Periodic DCA buy (drop={drop_from_high:.1%}, mult={multiplier:.1f}x)",
                confidence=0.5,
                risk_score=0.5,
                position_size_pct=min(position_size_pct, 0.5),
            ))
            last_buy_idx = position

        return StrategyResult(signals=signals)
