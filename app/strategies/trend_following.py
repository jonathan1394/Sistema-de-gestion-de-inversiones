"""Trend-following strategy combining EMA alignment, RSI, and volume filters."""

from __future__ import annotations

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult
from app.strategies.rsi_strategy import compute_rsi


class TrendFollowing(BaseStrategy):
    """Buy when price is above long EMA, EMAs are bullish, RSI is in range, and volume is elevated."""

    def _build_features(self, data: pd.DataFrame) -> pd.DataFrame:
        ema_long = self.parameters.get("ema_long", 200)
        ema_fast = self.parameters.get("ema_fast", 20)
        ema_slow = self.parameters.get("ema_slow", 50)
        rsi_period = self.parameters.get("rsi_period", 14)

        df = data.copy()
        df["ema_long"] = df["close"].ewm(span=ema_long, adjust=False).mean()
        df["ema_fast"] = df["close"].ewm(span=ema_fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=ema_slow, adjust=False).mean()
        df["rsi"] = compute_rsi(df["close"], rsi_period)
        df["volume_ma"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_ma"].replace(0, float("nan"))
        return df

    @staticmethod
    def _row_complete(row: pd.Series) -> bool:
        return not pd.isna(row["ema_long"]) and not pd.isna(row["ema_fast"]) and not pd.isna(row["rsi"]) and not pd.isna(row["volume_ratio"])

    def _buy_conditions_met(self, row: pd.Series) -> bool:
        rsi_min = self.parameters.get("rsi_min", 40)
        rsi_max = self.parameters.get("rsi_max", 70)
        volume_min = self.parameters.get("volume_min", 1.0)
        trend_up = row["close"] > row["ema_long"]
        ema_bullish = row["ema_fast"] > row["ema_slow"]
        rsi_ok = rsi_min <= row["rsi"] <= rsi_max
        volume_ok = row["volume_ratio"] > volume_min
        return trend_up and ema_bullish and rsi_ok and volume_ok

    @staticmethod
    def _trend_broken(row: pd.Series) -> bool:
        return row["close"] <= row["ema_long"]

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """Generate BUY when trend conditions align, SELL when trend breaks."""
        symbol = self.parameters.get("symbol", "UNKNOWN")
        df = self._build_features(data)

        signals: list[Signal] = []
        in_position = False

        for idx, row in df.iterrows():
            if not self._row_complete(row):
                continue
            timestamp = idx if isinstance(idx, pd.Timestamp) else pd.Timestamp(row.get("timestamp", idx))
            price = row["close"]

            if self._buy_conditions_met(row) and not in_position:
                signals.append(
                    Signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        action="BUY",
                        price=price,
                        reason="Trend up, EMAs bullish, RSI in range, volume above avg",
                        confidence=0.65,
                        risk_score=0.35,
                    )
                )
                in_position = True
                continue

            if self._trend_broken(row) and in_position:
                signals.append(
                    Signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        action="SELL",
                        price=price,
                        reason="Price closed below long-term EMA (trend broken)",
                        confidence=0.7,
                        risk_score=0.3,
                    )
                )
                in_position = False

        return StrategyResult(signals=signals)
