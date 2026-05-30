"""Trend-following strategy combining EMA alignment, RSI, and volume filters."""

from __future__ import annotations

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult
from app.strategies.rsi_strategy import compute_rsi


class TrendFollowing(BaseStrategy):
    """Buy when price is above long EMA, EMAs are bullish, RSI is in range, and volume is elevated."""

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """Generate BUY when trend conditions align, SELL when trend breaks."""
        ema_long = self.parameters.get("ema_long", 200)
        ema_fast = self.parameters.get("ema_fast", 20)
        ema_slow = self.parameters.get("ema_slow", 50)
        rsi_period = self.parameters.get("rsi_period", 14)
        rsi_min = self.parameters.get("rsi_min", 40)
        rsi_max = self.parameters.get("rsi_max", 70)
        volume_min = self.parameters.get("volume_min", 1.0)
        symbol = self.parameters.get("symbol", "UNKNOWN")

        df = data.copy()
        df["ema_long"] = df["close"].ewm(span=ema_long, adjust=False).mean()
        df["ema_fast"] = df["close"].ewm(span=ema_fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=ema_slow, adjust=False).mean()
        df["rsi"] = compute_rsi(df["close"], rsi_period)
        df["volume_ma"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma"].replace(0, float("nan"))

        signals: list[Signal] = []
        in_position = False

        for idx, row in df.iterrows():
            if pd.isna(row["ema_long"]) or pd.isna(row["ema_fast"]) or pd.isna(row["rsi"]) or pd.isna(row["volume_ratio"]):
                continue

            timestamp = idx if isinstance(idx, pd.Timestamp) else pd.Timestamp(row.get("timestamp", idx))
            price = row["close"]

            trend_up = row["close"] > row["ema_long"]
            ema_bullish = row["ema_fast"] > row["ema_slow"]
            rsi_ok = rsi_min <= row["rsi"] <= rsi_max
            volume_ok = row["volume_ratio"] > volume_min

            if trend_up and ema_bullish and rsi_ok and volume_ok and not in_position:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    action="BUY",
                    price=price,
                    reason="Trend up, EMAs bullish, RSI in range, volume above avg",
                    confidence=0.65,
                    risk_score=0.35,
                ))
                in_position = True

            elif not trend_up and in_position:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    action="SELL",
                    price=price,
                    reason="Price closed below long-term EMA (trend broken)",
                    confidence=0.7,
                    risk_score=0.3,
                ))
                in_position = False

        return StrategyResult(signals=signals)
