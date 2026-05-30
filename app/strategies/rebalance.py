"""Rebalancing strategy that maintains a target portfolio weight."""

from __future__ import annotations

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult


class RebalanceStrategy(BaseStrategy):
    """Buy or sell to restore the asset to its target weight within a threshold."""

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """Generate BUY/SELL signals to restore target portfolio weight."""
        target_pct = self.parameters.get("target_pct", 0.5)
        rebalance_threshold = self.parameters.get("rebalance_threshold", 0.05)
        rebalance_frequency = self.parameters.get("rebalance_frequency", 30)
        symbol = self.parameters.get("symbol", "UNKNOWN")

        df = data.copy()
        signals: list[Signal] = []
        last_rebalance_idx = -rebalance_frequency

        for idx, row in df.iterrows():
            timestamp = idx if isinstance(idx, pd.Timestamp) else pd.Timestamp(row.get("timestamp", idx))
            price = row["close"]

            position = df.index.get_loc(idx)
            if position < last_rebalance_idx + rebalance_frequency:
                continue

            if "current_weight" not in self.parameters:
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    action="BUY",
                    price=price,
                    reason="Initial position for rebalance strategy",
                    confidence=0.5,
                    risk_score=0.5,
                    position_size_pct=target_pct,
                ))
                last_rebalance_idx = position
                continue

            current_weight = self.parameters["current_weight"]
            deviation = current_weight - target_pct

            if abs(deviation) > rebalance_threshold:
                action = "SELL" if deviation > 0 else "BUY"
                rebalance_size = abs(deviation)

                signals.append(Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    action=action,
                    price=price,
                    reason=f"Rebalance: weight {current_weight:.1%} vs target {target_pct:.1%}",
                    confidence=0.7,
                    risk_score=0.3,
                    position_size_pct=rebalance_size,
                ))
                last_rebalance_idx = position

        return StrategyResult(signals=signals)
