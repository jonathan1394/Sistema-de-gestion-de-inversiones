"""Dynamic DCA strategy that increases investment size during deeper drops."""

from __future__ import annotations

import logging

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult

logger = logging.getLogger(__name__)

class DCADynamic(BaseStrategy):
    """Periodic dollar-cost averaging with dynamic position sizing based on drawdown."""

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """Generate periodic DCA BUY signals with dynamic sizing based on drawdown."""
        interval_days = self.parameters.get("interval_days", 7)
        drop_threshold_1 = self.parameters.get("drop_threshold_1", 0.10)
        drop_threshold_2 = self.parameters.get("drop_threshold_2", 0.20)
        increase_1 = self.parameters.get("increase_1", 1.5)
        increase_2 = self.parameters.get("increase_2", 2.0)
        ema_period = self.parameters.get("ema_period", 200)
        reduce_multiplier = self.parameters.get("reduce_multiplier", 0.5)
        symbol = self.parameters.get("symbol", "UNKNOWN")
        confidence = float(self.parameters.get("confidence", 0.5))
        risk_score = float(self.parameters.get("risk_score", 0.5))
        self.min_required_bars = int(self.parameters.get("min_required_bars", ema_period + 1))
        not_enough = self._check_min_bars(data)
        if not_enough is not None:
            return not_enough

        df = data.copy()
        df["ema_long"] = df["close"].ewm(span=ema_period, adjust=False).mean()
        df["max_recent"] = df["close"].rolling(window=30).max()
        df["drop_from_high"] = (df["max_recent"] - df["close"]) / df["max_recent"]
        df["below_ema"] = df["close"] < df["ema_long"]

        max_ok = df["max_recent"].notna() & (df["max_recent"] > 0)
        positions = pd.Series(range(len(df)), index=df.index)
        buy_day = positions % interval_days == 0

        mask = max_ok & buy_day
        buy_idx = df.index[mask]

        signals: list[Signal] = []
        for idx in buy_idx:
            row = df.loc[idx]
            drop = row["drop_from_high"]
            below = row["below_ema"] if not pd.isna(row["ema_long"]) else False

            if drop >= drop_threshold_2:
                multiplier = increase_2
            elif drop >= drop_threshold_1:
                multiplier = increase_1
            else:
                multiplier = 1.0

            if below:
                multiplier *= reduce_multiplier

            position_size_pct = 0.1 * multiplier

            price = row["close"]
            signals.append(Signal(
                symbol=symbol,
                timestamp=pd.Timestamp(idx),
                action="BUY",
                price=price,
                reason=f"Periodic DCA buy (drop={drop:.1%}, mult={multiplier:.1f}x)",
                confidence=confidence,
                risk_score=risk_score,
                position_size_pct=min(position_size_pct, 0.5),
                stop_loss=price * (1 - self.stop_loss_pct),
                take_profit=price * (1 + self.take_profit_pct),
            ))

        return StrategyResult(signals=signals)
