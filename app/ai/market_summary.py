from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class MarketCondition:
    trend: str
    volatility: str
    volume_profile: str
    rsi_condition: str
    summary: str


@dataclass
class MarketSummary:
    symbol: str
    period: str
    start_date: str
    end_date: str
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    return_pct: float
    volatility_pct: float
    avg_volume: float
    condition: MarketCondition
    key_levels: dict[str, float]


def generate_market_summary(
    data: pd.DataFrame,
    symbol: str = "UNKNOWN",
    period: str = "daily",
) -> MarketSummary:
    df = data.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    if df.empty:
        raise ValueError("No data provided for market summary")

    open_px = float(df.iloc[0]["open"]) if "open" in df.columns else float(df.iloc[0]["close"])
    close_px = float(df.iloc[-1]["close"])
    high_px = float(df["high"].max()) if "high" in df.columns else close_px
    low_px = float(df["low"].min()) if "low" in df.columns else close_px
    ret = (close_px - open_px) / open_px * 100

    returns = df["close"].pct_change().dropna()
    volatility = float(returns.std() * 100)

    avg_volume = float(df["volume"].mean()) if "volume" in df.columns else 0.0

    ema_20 = df["close"].ewm(span=20, adjust=False).mean()
    ema_50 = df["close"].ewm(span=50, adjust=False).mean()
    last_ema20 = float(ema_20.iloc[-1]) if len(ema_20) > 0 else close_px
    last_ema50 = float(ema_50.iloc[-1]) if len(ema_50) > 0 else close_px

    if close_px > last_ema20 > last_ema50:
        trend = "strong_up"
    elif close_px > last_ema50:
        trend = "up"
    elif close_px < last_ema20 < last_ema50:
        trend = "strong_down"
    elif close_px < last_ema50:
        trend = "down"
    else:
        trend = "sideways"

    if volatility < 0.5:
        vol_cond = "low"
    elif volatility < 1.5:
        vol_cond = "moderate"
    else:
        vol_cond = "high"

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=14, adjust=False).mean()
    avg_loss = loss.ewm(span=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi_series = 100 - (100 / (1 + rs))
    last_rsi = float(rsi_series.iloc[-1]) if len(rsi_series) > 0 and not pd.isna(rsi_series.iloc[-1]) else 50.0

    if last_rsi < 30:
        rsi_cond = "oversold"
    elif last_rsi > 70:
        rsi_cond = "overbought"
    else:
        rsi_cond = "neutral"

    if "volume" in df.columns:
        vol_ma = df["volume"].rolling(20).mean()
        vol_ratio = float((df["volume"] / vol_ma.replace(0, float("nan"))).iloc[-1]) if len(vol_ma) > 0 else 1.0
        if vol_ratio > 1.5:
            vol_profile = "high"
        elif vol_ratio > 1.0:
            vol_profile = "above_average"
        else:
            vol_profile = "normal"
    else:
        vol_profile = "unknown"

    summary_parts = []
    summary_parts.append(f"{'Uptrend' if 'up' in trend else 'Downtrend' if 'down' in trend else 'Sideways'} with {vol_cond} volatility")
    if rsi_cond != "neutral":
        summary_parts.append(f"RSI suggests {rsi_cond} ({last_rsi:.0f})")
    if ret > 0:
        summary_parts.append(f"positive return of {ret:+.2f}%")
    else:
        summary_parts.append(f"negative return of {ret:+.2f}%")
    if vol_profile == "high":
        summary_parts.append("elevated volume")

    key_levels = {}
    key_levels["support"] = round(low_px, 2)
    key_levels["resistance"] = round(high_px, 2)
    key_levels["ema_20"] = round(last_ema20, 2)
    key_levels["ema_50"] = round(last_ema50, 2)

    return MarketSummary(
        symbol=symbol,
        period=period,
        start_date=str(df.index[0].date()),
        end_date=str(df.index[-1].date()),
        open_price=round(open_px, 2),
        close_price=round(close_px, 2),
        high_price=round(high_px, 2),
        low_price=round(low_px, 2),
        return_pct=round(ret, 2),
        volatility_pct=round(volatility, 2),
        avg_volume=round(avg_volume, 2),
        condition=MarketCondition(
            trend=trend,
            volatility=vol_cond,
            volume_profile=vol_profile,
            rsi_condition=rsi_cond,
            summary=". ".join(summary_parts),
        ),
        key_levels=key_levels,
    )


def format_summary(summary: MarketSummary) -> str:
    lines = []
    lines.append(f"=== Market Summary: {summary.symbol} ({summary.period}) ===")
    lines.append(f"Period: {summary.start_date} → {summary.end_date}")
    lines.append(f"Price: ${summary.open_price} → ${summary.close_price} ({summary.return_pct:+.2f}%)")
    lines.append(f"Range: ${summary.low_price} - ${summary.high_price}")
    lines.append(f"Volatility: {summary.volatility_pct:.2f}%")
    lines.append(f"Avg Volume: {summary.avg_volume:.0f}")
    lines.append("")
    lines.append("Market Condition:")
    lines.append(f"  Trend: {summary.condition.trend}")
    lines.append(f"  Volatility: {summary.condition.volatility}")
    lines.append(f"  RSI: {summary.condition.rsi_condition}")
    lines.append(f"  Volume: {summary.condition.volume_profile}")
    lines.append(f"  Summary: {summary.condition.summary}")
    lines.append("")
    lines.append("Key Levels:")
    for level, price in summary.key_levels.items():
        lines.append(f"  {level}: ${price}")
    return "\n".join(lines)
