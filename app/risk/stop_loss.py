"""Stop-loss helpers for fixed and ATR-based risk control."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class StopLossResult:
    stop_price: float
    distance_pct: float
    method: str
    rejected: bool = False
    rejection_reason: str = ""


def fixed_percentage(
    entry_price: float,
    stop_loss_pct: float = 0.02,
    direction: str = "long",
    min_stop_pct: float = 0.005,
    max_stop_pct: float = 0.10,
) -> StopLossResult:
    """Build a stop-loss from a fixed percentage distance from entry."""
    if stop_loss_pct < min_stop_pct:
        return StopLossResult(
            stop_price=0, distance_pct=0, method="fixed_pct",
            rejected=True,
            rejection_reason=f"Stop {stop_loss_pct:.1%} below minimum {min_stop_pct:.1%}",
        )
    if stop_loss_pct > max_stop_pct:
        return StopLossResult(
            stop_price=0, distance_pct=0, method="fixed_pct",
            rejected=True,
            rejection_reason=f"Stop {stop_loss_pct:.1%} exceeds maximum {max_stop_pct:.1%}",
        )

    if direction == "long":
        stop_price = entry_price * (1 - stop_loss_pct)
    else:
        stop_price = entry_price * (1 + stop_loss_pct)

    return StopLossResult(
        stop_price=round(stop_price, 2),
        distance_pct=stop_loss_pct,
        method="fixed_pct",
    )


def atr_based(
    entry_price: float,
    atr_value: float,
    atr_multiplier: float = 2.0,
    direction: str = "long",
    min_stop_pct: float = 0.005,
    max_stop_pct: float = 0.10,
) -> StopLossResult:
    """Build a stop-loss based on ATR distance clamped by min/max bounds."""
    if atr_value <= 0:
        return StopLossResult(
            stop_price=0, distance_pct=0, method="atr",
            rejected=True, rejection_reason="ATR must be positive",
        )

    distance = atr_value * atr_multiplier
    distance_pct = distance / entry_price if entry_price > 0 else 0

    if distance_pct < min_stop_pct:
        distance = entry_price * min_stop_pct
        distance_pct = min_stop_pct
    if distance_pct > max_stop_pct:
        distance = entry_price * max_stop_pct
        distance_pct = max_stop_pct

    if direction == "long":
        stop_price = entry_price - distance
    else:
        stop_price = entry_price + distance

    return StopLossResult(
        stop_price=round(max(stop_price, 0), 2),
        distance_pct=distance_pct,
        method="atr",
    )


def take_profit_dynamic(
    entry_price: float,
    atr_value: float,
    atr_multiplier: float = 3.0,
    direction: str = "long",
    min_tp_pct: float = 0.01,
    max_tp_pct: float = 0.20,
) -> StopLossResult:
    """Calculate a dynamic take-profit based on ATR distance clamped by min/max bounds."""
    if atr_value <= 0:
        return StopLossResult(
            stop_price=0, distance_pct=0, method="atr_tp",
            rejected=True, rejection_reason="ATR must be positive",
        )

    distance = atr_value * atr_multiplier
    distance_pct = distance / entry_price if entry_price > 0 else 0

    if distance_pct < min_tp_pct:
        distance = entry_price * min_tp_pct
        distance_pct = min_tp_pct
    if distance_pct > max_tp_pct:
        distance = entry_price * max_tp_pct
        distance_pct = max_tp_pct

    if direction == "long":
        tp_price = entry_price + distance
    else:
        tp_price = entry_price - distance

    return StopLossResult(
        stop_price=round(max(tp_price, 0), 2),
        distance_pct=distance_pct,
        method="atr_tp",
    )
