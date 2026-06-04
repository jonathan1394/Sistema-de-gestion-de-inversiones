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

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """Generate BUY when trend conditions align, SELL when trend breaks."""
        symbol = self.parameters.get("symbol", "UNKNOWN")
        rsi_min = self.parameters.get("rsi_min", 40)
        rsi_max = self.parameters.get("rsi_max", 70)
        volume_min = self.parameters.get("volume_min", 1.0)
        ema_long = self.parameters.get("ema_long", 200)
        self.min_required_bars = int(self.parameters.get("min_required_bars", ema_long + 1))
        not_enough = self._check_min_bars(data)
        if not_enough is not None:
            return not_enough
        df = self._build_features(data)

        trend_up = df["close"] > df["ema_long"]
        ema_bullish = df["ema_fast"] > df["ema_slow"]
        rsi_ok = df["rsi"].between(rsi_min, rsi_max)
        volume_ok = df["volume_ratio"] > volume_min
        all_ok = trend_up & ema_bullish & rsi_ok & volume_ok

        ready = all_ok & all_ok.notna()
        trend_broken = (df["close"] <= df["ema_long"]) & df["ema_long"].notna()

        entry = ready & ~ready.shift(1).fillna(False)
        exit_ = trend_broken & ~trend_broken.shift(1).fillna(False)

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
                    reason="Trend up, EMAs bullish, RSI in range, volume above avg",
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
                    reason="Price closed below long-term EMA (trend broken)",
                    confidence=self.confidence,
                    risk_score=self.risk_score,
                )
            )

        return StrategyResult(signals=signals)
