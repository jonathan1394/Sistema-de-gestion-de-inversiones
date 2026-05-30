from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.strategies.base_strategy import Signal


@dataclass
class SignalExplanation:
    signal: Signal
    explanation: str
    context: dict[str, float]
    strength: str
    risk_note: str


def explain_signal(
    signal: Signal,
    data: Optional[pd.DataFrame] = None,
) -> SignalExplanation:
    context: dict[str, float] = {}
    strength = "medium"
    risk_note = ""

    if signal.action == "BUY":
        explanation = _explain_buy(signal, data, context)
    elif signal.action == "SELL":
        explanation = _explain_sell(signal, data, context)
    elif signal.action == "EXIT":
        explanation = f"Full exit signal for {signal.symbol}: {signal.reason}"
        strength = "high"
    elif signal.action == "REDUCE":
        explanation = f"Reduce position for {signal.symbol}: {signal.reason}"
        strength = "medium"
    else:
        explanation = f"HOLD: No clear signal for {signal.symbol}"

    if signal.confidence >= 0.7:
        strength = "high"
    elif signal.confidence <= 0.4:
        strength = "low"

    if data is not None and "close" in data.columns:
        price = data["close"].iloc[-1] if hasattr(data["close"], "iloc") else float(data["close"])
        context["current_price"] = round(float(price), 2)

        if "volume" in data.columns:
            vol_series = data["volume"]
            avg_vol = vol_series.tail(20).mean()
            last_vol = vol_series.iloc[-1]
            if avg_vol > 0:
                context["volume_ratio"] = round(float(last_vol / avg_vol), 2)

    if signal.stop_loss is not None:
        risk_pct = abs(signal.price - signal.stop_loss) / signal.price * 100
        context["stop_distance_pct"] = round(risk_pct, 2)
        if risk_pct > 5:
            risk_note = f"Wide stop ({risk_pct:.1f}%) — consider reducing position size"
        elif risk_pct < 0.5:
            risk_note = f"Tight stop ({risk_pct:.1f}%) — risk of early exit"
        else:
            risk_note = f"Stop at {risk_pct:.1f}% — within normal range"

    if signal.take_profit is not None:
        tp_pct = abs(signal.take_profit - signal.price) / signal.price * 100
        context["take_profit_pct"] = round(tp_pct, 2)

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
    parts = [f"SELL signal for {signal.symbol}"]
    parts.append(f"Reason: {signal.reason}")

    if signal.pnl_pct is not None:
        parts.append(f"P&L: {signal.pnl_pct:+.2f}%")

    context["exit_price"] = round(signal.price, 2)

    return ". ".join(parts)


def batch_explain(
    signals: list[Signal],
    data: Optional[pd.DataFrame] = None,
) -> list[SignalExplanation]:
    return [explain_signal(s, data) for s in signals]
