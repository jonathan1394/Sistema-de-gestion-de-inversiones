"""Market summary generation from OHLCV data."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class MarketCondition:
    """Qualitative market condition labels and short summary."""

    trend: str
    volatility: str
    volume_profile: str
    rsi_condition: str
    summary: str


@dataclass
class MarketSummary:
    """Structured summary of price action and derived indicators."""

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


def _prepare_frame(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize input data into a sorted datetime-indexed frame."""
    df = data.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    if df.empty:
        raise ValueError("No data provided for market summary")
    return df


def _market_trend(close_px: float, ema20: float, ema50: float) -> str:
    """Classify trend state from close price and EMA alignment."""
    if close_px > ema20 > ema50:
        return "strong_up"
    if close_px > ema50:
        return "up"
    if close_px < ema20 < ema50:
        return "strong_down"
    if close_px < ema50:
        return "down"
    return "sideways"


def _volatility_label(volatility: float) -> str:
    """Map volatility value to discrete bucket label."""
    if volatility < 0.5:
        return "low"
    if volatility < 1.5:
        return "moderate"
    return "high"


def _rsi_label(rsi: float) -> str:
    """Map RSI value to overbought/oversold/neutral label."""
    if rsi < 30:
        return "oversold"
    if rsi > 70:
        return "overbought"
    return "neutral"


def _volume_profile(frame: pd.DataFrame) -> str:
    """Classify latest volume relative to its recent moving average."""
    if "volume" not in frame.columns:
        return "unknown"
    vol_ma = frame["volume"].rolling(20).mean()
    vol_ratio = (
        float((frame["volume"] / vol_ma.replace(0, float("nan"))).iloc[-1])
        if len(vol_ma) > 0
        else 1.0
    )
    if vol_ratio > 1.5:
        return "high"
    if vol_ratio > 1.0:
        return "above_average"
    return "normal"


def _summary_parts(
    trend: str, vol_cond: str, rsi_cond: str, last_rsi: float, ret: float, vol_profile: str
) -> list[str]:
    """Compose sentence fragments for the condition summary."""
    trend_label = "Uptrend" if "up" in trend else "Downtrend" if "down" in trend else "Sideways"
    parts = [f"{trend_label} with {vol_cond} volatility"]
    if rsi_cond != "neutral":
        parts.append(f"RSI suggests {rsi_cond} ({last_rsi:.0f})")
    parts.append(
        f"positive return of {ret:+.2f}%" if ret > 0 else f"negative return of {ret:+.2f}%"
    )
    if vol_profile == "high":
        parts.append("elevated volume")
    return parts


def _price_stats(df: pd.DataFrame) -> tuple[float, float, float, float, float, float]:
    """Compute core price and volatility statistics from frame."""
    open_px = float(df.iloc[0]["open"]) if "open" in df.columns else float(df.iloc[0]["close"])
    close_px = float(df.iloc[-1]["close"])
    high_px = float(df["high"].max()) if "high" in df.columns else close_px
    low_px = float(df["low"].min()) if "low" in df.columns else close_px
    ret = (close_px - open_px) / open_px * 100
    returns = df["close"].pct_change().dropna()
    volatility = float(returns.std() * 100)
    return open_px, close_px, high_px, low_px, ret, volatility


def _ema_levels(df: pd.DataFrame, close_px: float) -> tuple[float, float]:
    """Return latest EMA20 and EMA50 levels."""
    ema_20 = df["close"].ewm(span=20, adjust=False).mean()
    ema_50 = df["close"].ewm(span=50, adjust=False).mean()
    last_ema20 = float(ema_20.iloc[-1]) if len(ema_20) > 0 else close_px
    last_ema50 = float(ema_50.iloc[-1]) if len(ema_50) > 0 else close_px
    return last_ema20, last_ema50


def _last_rsi(df: pd.DataFrame) -> float:
    """Compute latest RSI value with EMA smoothing."""
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=14, adjust=False).mean()
    avg_loss = loss.ewm(span=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi_series = 100 - (100 / (1 + rs))
    if len(rsi_series) == 0 or pd.isna(rsi_series.iloc[-1]):
        return 50.0
    return float(rsi_series.iloc[-1])


def generate_market_summary(
    data: pd.DataFrame,
    symbol: str = "UNKNOWN",
    period: str = "daily",
) -> MarketSummary:
    """Build a structured market summary for a symbol and period."""
    df = _prepare_frame(data)
    open_px, close_px, high_px, low_px, ret, volatility = _price_stats(df)
    avg_volume = float(df["volume"].mean()) if "volume" in df.columns else 0.0
    last_ema20, last_ema50 = _ema_levels(df, close_px)
    trend = _market_trend(close_px, last_ema20, last_ema50)
    vol_cond = _volatility_label(volatility)
    last_rsi = _last_rsi(df)
    rsi_cond = _rsi_label(last_rsi)
    vol_profile = _volume_profile(df)
    summary_parts = _summary_parts(trend, vol_cond, rsi_cond, last_rsi, ret, vol_profile)
    key_levels = {
        "support": round(low_px, 2),
        "resistance": round(high_px, 2),
        "ema_20": round(last_ema20, 2),
        "ema_50": round(last_ema50, 2),
    }

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
    """Render a human-readable text summary from market metrics."""
    lines = []
    lines.append(f"=== Market Summary: {summary.symbol} ({summary.period}) ===")
    lines.append(f"Period: {summary.start_date} → {summary.end_date}")
    lines.append(
        f"Price: ${summary.open_price} → ${summary.close_price} ({summary.return_pct:+.2f}%)"
    )
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
