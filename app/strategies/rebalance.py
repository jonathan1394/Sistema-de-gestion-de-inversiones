"""Rebalancing strategy that maintains a target portfolio weight."""

from __future__ import annotations

import logging

import pandas as pd

from app.strategies.base_strategy import BaseStrategy, Signal, StrategyResult

logger = logging.getLogger(__name__)

class RebalanceStrategy(BaseStrategy):
    """Buy or sell to restore the asset to its target weight within a threshold."""

    def generate_signals(self, data: pd.DataFrame) -> StrategyResult:
        """Generate BUY/SELL signals to restore target portfolio weight."""
        target_pct = self.parameters.get("target_pct", 0.5)
        rebalance_threshold = self.parameters.get("rebalance_threshold", 0.05)
        rebalance_frequency = self.parameters.get("rebalance_frequency", 30)
        symbol = self.parameters.get("symbol", "UNKNOWN")
        confidence = float(self.parameters.get("confidence", 0.6))
        risk_score = float(self.parameters.get("risk_score", 0.4))
        self.min_required_bars = int(self.parameters.get("min_required_bars", 2))
        not_enough = self._check_min_bars(data)
        if not_enough is not None:
            return not_enough

        df = data.copy()
        positions = pd.Series(range(len(df)), index=df.index)
        rebalance_day = positions % rebalance_frequency == 0
        rebalance_idx = df.index[rebalance_day]

        signals: list[Signal] = []

        if "current_weight" not in self.parameters:
            if len(rebalance_idx) > 0:
                idx = rebalance_idx[0]
                price = df.loc[idx, "close"]
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=pd.Timestamp(idx),
                    price=price,
                    action="BUY",
                    reason="Initial position for rebalance strategy",
                    confidence=confidence,
                    risk_score=risk_score,
                    position_size_pct=target_pct,
                    stop_loss=price * (1 - self.stop_loss_pct),
                    take_profit=price * (1 + self.take_profit_pct),
                ))
            return StrategyResult(signals=signals)

        current_weight = self.parameters["current_weight"]
        deviation = current_weight - target_pct

        if abs(deviation) > rebalance_threshold:
            action = "SELL" if deviation > 0 else "BUY"
            rebalance_size = abs(deviation)

            for idx in rebalance_idx:
                price = df.loc[idx, "close"]
                signals.append(Signal(
                    symbol=symbol,
                    timestamp=pd.Timestamp(idx),
                    price=price,
                    action=action,
                    reason=f"Rebalance: weight {current_weight:.1%} vs target {target_pct:.1%}",
                    confidence=confidence,
                    risk_score=risk_score,
                    position_size_pct=rebalance_size,
                    stop_loss=price * (1 - self.stop_loss_pct) if action == "BUY" else None,
                    take_profit=price * (1 + self.take_profit_pct) if action == "BUY" else None,
                ))

        return StrategyResult(signals=signals)
