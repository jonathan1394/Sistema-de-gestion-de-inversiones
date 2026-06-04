"""RSI-based strategy that buys on oversold and sells on overbought crossovers."""

from __future__ import annotations

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute Relative Strength Index for a price series."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi


class RSIStrategy(BaseStrategy):
    """Generate signals when RSI crosses oversold/overbought thresholds."""

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """Generate BUY/SELL signals on RSI crossing oversold/overbought thresholds."""
        rsi_period = self.parameters.get("rsi_period", 14)
        oversold = self.parameters.get("oversold", 30)
        overbought = self.parameters.get("overbought", 70)
        symbol = self.parameters.get("symbol", "UNKNOWN")
        self.min_required_bars = int(self.parameters.get("min_required_bars", rsi_period + 1))
        not_enough = self._check_min_bars(data)
        if not_enough is not None:
            return not_enough

        df = data.copy()
        df["rsi"] = compute_rsi(df["close"], rsi_period)
        df["prev_rsi"] = df["rsi"].shift(1)

        entry = (df["prev_rsi"] <= oversold) & (df["rsi"] > oversold) & df["rsi"].notna()
        exit_ = (df["prev_rsi"] >= overbought) & (df["rsi"] < overbought) & df["rsi"].notna()

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
                    reason=f"RSI crossed above {oversold} (oversold)",
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
                    reason=f"RSI crossed below {overbought} (overbought)",
                    confidence=self.confidence,
                    risk_score=self.risk_score,
                )
            )

        return StrategyResult(signals=signals)
