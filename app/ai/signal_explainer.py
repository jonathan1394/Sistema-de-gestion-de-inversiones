"""Natural-language explanations for trading signals."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd

from app.strategies.base_strategy import Signal

logger = logging.getLogger(__name__)

@dataclass
class SignalExplanation:
    """Narrative explanation and context for a trading signal."""

    signal: Signal
    explanation: str
    context: dict[str, float]
    strength: str
    risk_note: str


def _action_explanation(signal: Signal, data: Optional[pd.DataFrame], context: dict[str, float]) -> tuple[str, str]:
    """Build action-specific explanation text and base strength."""
    action_map: dict[str, tuple[str, str] | Callable] = {
        "BUY": lambda: _explain_buy(signal, data, context),
        "SELL": lambda: _explain_sell(signal, data, context),
        "EXIT": (f"Full exit signal for {signal.symbol}: {signal.reason}", "high"),
        "REDUCE": (f"Reduce position for {signal.symbol}: {signal.reason}", "medium"),
    }
    raw = action_map.get(signal.action)
    if raw is None:
        return f"HOLD: No clear signal for {signal.symbol}", "medium"
    if callable(raw):
        return raw(), "medium"
    return raw


def _confidence_strength(confidence: float, current: str) -> str:
    """Adjust strength label using explicit confidence value."""
    if confidence >= 0.7:
        return "high"
    if confidence <= 0.4:
        return "low"
    return current


def _build_price_context(data: Optional[pd.DataFrame], context: dict[str, float]) -> None:
    """Populate context with current price and volume ratio."""
    if data is None or "close" not in data.columns:
        return
    price = data["close"].iloc[-1] if hasattr(data["close"], "iloc") else float(data["close"])
    context["current_price"] = round(float(price), 2)
    if "volume" in data.columns:
        vol_series = data["volume"]
        avg_vol = vol_series.tail(20).mean()
        last_vol = vol_series.iloc[-1]
        if avg_vol > 0:
            context["volume_ratio"] = round(float(last_vol / avg_vol), 2)


def _stop_risk_note(signal: Signal, context: dict[str, float]) -> str:
    """Generate stop-distance risk note and enrich context."""
    if signal.stop_loss is None:
        return ""
    risk_pct = abs(signal.price - signal.stop_loss) / signal.price * 100
    context["stop_distance_pct"] = round(risk_pct, 2)
    if risk_pct > 5:
        return f"Wide stop ({risk_pct:.1f}%) -- consider reducing position size"
    if risk_pct < 0.5:
        return f"Tight stop ({risk_pct:.1f}%) -- risk of early exit"
    return f"Stop at {risk_pct:.1f}% -- within normal range"


def _take_profit_context(signal: Signal, context: dict[str, float]) -> None:
    """Populate take-profit distance percentage in context."""
    if signal.take_profit is None:
        return
    tp_pct = abs(signal.take_profit - signal.price) / signal.price * 100
    context["take_profit_pct"] = round(tp_pct, 2)


def explain_signal(
    signal: Signal,
    data: Optional[pd.DataFrame] = None,
) -> SignalExplanation:
    """Explain a single signal with context, strength, and risk notes."""
    context: dict[str, float] = {}

    explanation, strength = _action_explanation(signal, data, context)
    strength = _confidence_strength(signal.confidence, strength)
    _build_price_context(data, context)
    risk_note = _stop_risk_note(signal, context)
    _take_profit_context(signal, context)

    return SignalExplanation(
        signal=signal,
        explanation=explanation,
        context=context,
        strength=strength,
        risk_note=risk_note,
    )


def _explain_buy(
    signal: Signal,
    data: Optional[pd.DataFrame],
    context: dict[str, float],
) -> str:
    """Build explanatory text for BUY signals."""
    parts = [f"BUY signal for {signal.symbol}"]
    parts.append(f"Reason: {signal.reason}")
    parts.append(f"Price: ${signal.price:.2f}")

    if data is not None and len(data) > 20:
        close = data["close"]
        ema_20 = close.ewm(span=20).mean().iloc[-1]
        ema_50 = close.ewm(span=50).mean().iloc[-1] if len(close) > 50 else None
        context["ema_20"] = round(float(ema_20), 2)
        if ema_50:
            context["ema_50"] = round(float(ema_50), 2)

        if float(close.iloc[-1]) > float(ema_20):
            parts.append("Price above 20-EMA (short-term bullish)")
        if ema_50 and float(ema_20) > float(ema_50):
            parts.append("20-EMA above 50-EMA (medium-term bullish)")

    if signal.confidence > 0:
        parts.append(f"Confidence: {signal.confidence:.0%}")
    if signal.risk_score > 0:
        parts.append(f"Risk score: {signal.risk_score:.0%}")
        if signal.risk_score > 0.7:
            parts.append("⚠️ High risk score — ensure position sizing is conservative")

    return ". ".join(parts)


def _explain_sell(
    signal: Signal,
    data: Optional[pd.DataFrame],
    context: dict[str, float],
) -> str:
    """Build explanatory text for SELL/exit signals."""
    parts = [f"SELL signal for {signal.symbol}"]
    parts.append(f"Reason: {signal.reason}")

    pnl = context.get("pnl_pct")
    if pnl is not None:
        parts.append(f"P&L: {pnl:+.2f}%")

    context["exit_price"] = round(signal.price, 2)

    return ". ".join(parts)


def batch_explain(
    signals: list[Signal],
    data: Optional[pd.DataFrame] = None,
) -> list[SignalExplanation]:
    """Explain a batch of signals using shared optional market data."""
    return [explain_signal(s, data) for s in signals]
