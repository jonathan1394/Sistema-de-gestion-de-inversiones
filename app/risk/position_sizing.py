"""Position sizing logic based on risk-per-trade constraints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PositionSizeResult:
    position_size: float
    position_value: float
    risk_amount: float
    risk_pct: float
    entry_price: float
    stop_loss: float
    max_risk_pct: float
    rejected: bool = False
    rejection_reason: str = ""


def calculate_position_size(
    capital: float,
    entry_price: float,
    stop_loss: float,
    risk_per_trade_pct: float = 0.01,
    max_position_pct: float = 0.03,
    direction: str = "long",
) -> PositionSizeResult:
    """Calculate position quantity and value from entry, stop-loss, and capital."""
    if capital <= 0:
        return PositionSizeResult(
            position_size=0, position_value=0, risk_amount=0, risk_pct=0,
            entry_price=entry_price, stop_loss=stop_loss,
            max_risk_pct=risk_per_trade_pct,
            rejected=True, rejection_reason="Capital must be positive",
        )

    if entry_price <= 0 or stop_loss <= 0:
        return PositionSizeResult(
            position_size=0, position_value=0, risk_amount=0, risk_pct=0,
            entry_price=entry_price, stop_loss=stop_loss,
            max_risk_pct=risk_per_trade_pct,
            rejected=True, rejection_reason="Prices must be positive",
        )

    if direction == "long":
        if stop_loss >= entry_price:
            return PositionSizeResult(
                position_size=0, position_value=0, risk_amount=0, risk_pct=0,
                entry_price=entry_price, stop_loss=stop_loss,
                max_risk_pct=risk_per_trade_pct,
                rejected=True,
                rejection_reason="Stop-loss must be below entry for long",
            )
        price_risk = entry_price - stop_loss
    else:
        if stop_loss <= entry_price:
            return PositionSizeResult(
                position_size=0, position_value=0, risk_amount=0, risk_pct=0,
                entry_price=entry_price, stop_loss=stop_loss,
                max_risk_pct=risk_per_trade_pct,
                rejected=True,
                rejection_reason="Stop-loss must be above entry for short",
            )
        price_risk = stop_loss - entry_price

    risk_amount = capital * risk_per_trade_pct
    position_value = risk_amount / (price_risk / entry_price)
    max_position_value = capital * max_position_pct
    position_value = min(position_value, max_position_value)
    position_size = position_value / entry_price

    return PositionSizeResult(
        position_size=round(position_size, 8),
        position_value=round(position_value, 2),
        risk_amount=round(risk_amount, 2),
        risk_pct=risk_per_trade_pct * 100,
        entry_price=entry_price,
        stop_loss=stop_loss,
        max_risk_pct=risk_per_trade_pct,
    )
