from __future__ import annotations

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi


class RSIStrategy(BaseStrategy):
    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        rsi_period = self.parameters.get("rsi_period", 14)
        oversold = self.parameters.get("oversold", 30)
        overbought = self.parameters.get("overbought", 70)
        symbol = self.parameters.get("symbol", "UNKNOWN")

        df = data.copy()
        df["rsi"] = compute_rsi(df["close"], rsi_period)
        df["prev_rsi"] = df["rsi"].shift(1)

        signals: list[Signal] = []
        in_position = False

        for idx, row in df.iterrows():
            if pd.isna(row["rsi"]) or pd.isna(row["prev_rsi"]):
                continue

            timestamp = idx if isinstance(idx, pd.Timestamp) else pd.Timestamp(row.get("timestamp", idx))
            price = row["close"]

            buy_signal = row["prev_rsi"] <= oversold and row["rsi"] > oversold
            sell_signal = row["prev_rsi"] >= overbought and row["rsi"] < overbought

            if buy_signal and not in_position:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    action="BUY",
                    price=price,
                    reason=f"RSI crossed above {oversold} (oversold)",
                    confidence=0.5,
                    risk_score=0.5,
                ))
                in_position = True

            elif sell_signal and in_position:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    action="SELL",
                    price=price,
                    reason=f"RSI crossed below {overbought} (overbought)",
                    confidence=0.5,
                    risk_score=0.5,
                ))
                in_position = False

        return StrategyResult(signals=signals)
