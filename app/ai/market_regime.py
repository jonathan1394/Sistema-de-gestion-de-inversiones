"""Market regime classification from OHLCV data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

REGIME_LABELS = ("bull", "bear", "range", "high_volatility", "panic")


@dataclass
class RegimeResult:
    """Result of market regime classification."""

    regime: str
    confidence: float
    trend_strength: float
    volatility_regime: str
    adx: float
    rsi: float
    volume_ratio: float
    signal: str
    details: dict[str, float] = field(default_factory=dict)


def _prepare_frame(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize input data into a sorted datetime-indexed frame."""
    df = data.copy()
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    if df.empty:
        raise ValueError("No data provided for regime classification")
    return df


def _ema(
    series: pd.Series, period: int, column: Optional[pd.Series] = None
) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat(
        [
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _adx(df: pd.DataFrame, period: int = 14) -> float:
    high, low, close = df["high"], df["low"], df["close"]
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = pd.concat(
        [high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()],
        axis=1,
    ).max(axis=1)
    atr_val = tr.rolling(period).mean()
    eps = 1e-10
    atr_safe = atr_val.clip(lower=eps)
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr_safe)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr_safe)
    di_sum = (plus_di + minus_di).clip(lower=eps)
    dx = ((plus_di - minus_di).abs() / di_sum * 100)
    adx_series = dx.rolling(period).mean()
    if len(adx_series) == 0 or pd.isna(adx_series.iloc[-1]):
        return 25.0
    return float(adx_series.iloc[-1])


def _rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    if len(rsi_series) == 0 or pd.isna(rsi_series.iloc[-1]):
        return 50.0
    return float(rsi_series.iloc[-1])


def _volume_ratio(df: pd.DataFrame, period: int = 20) -> float:
    if "volume" not in df.columns:
        return 1.0
    vol_ma = df["volume"].rolling(period).mean()
    latest_vol = float(df["volume"].iloc[-1]) if len(df) > 0 else 1.0
    latest_ma = float(vol_ma.iloc[-1]) if len(vol_ma) > 0 else 1.0
    if latest_ma == 0:
        return 1.0
    return latest_vol / latest_ma


def _volatility_regime(
    df: pd.DataFrame, period: int = 20
) -> tuple[str, float]:
    returns = df["close"].pct_change().dropna()
    if len(returns) < period:
        vol = float(returns.std() * 100)
    else:
        vol = float(returns.tail(period).std() * 100)
    vol_20 = returns.rolling(period).std().dropna() * 100
    hist_vol = float(vol_20.mean()) if len(vol_20) > 0 else vol
    vol_ratio = vol / hist_vol if hist_vol > 0 else 1.0
    if vol > hist_vol * 2.5:
        return "panic", vol_ratio
    if vol > hist_vol * 1.5:
        return "high", vol_ratio
    if vol < hist_vol * 0.5:
        return "low", vol_ratio
    return "normal", vol_ratio


def classify_regime(
    data: pd.DataFrame,
    trend_period: int = 50,
) -> RegimeResult:
    """Classify the current market regime from OHLCV data.

    Returns one of: bull, bear, range, high_volatility, panic.
    """
    df = _prepare_frame(data)
    close = df["close"]
    ema_20 = _ema(close, 20)
    ema_50 = _ema(close, max(20, trend_period))
    last_ema20 = float(ema_20.iloc[-1]) if len(ema_20) > 0 else float(close.iloc[-1])
    last_ema50 = float(ema_50.iloc[-1]) if len(ema_50) > 0 else float(close.iloc[-1])
    last_close = float(close.iloc[-1])

    adx_val = _adx(df)
    rsi_val = _rsi(close)
    vol_regime, vol_ratio = _volatility_regime(df)
    vol_ratio_val = _volume_ratio(df)

    trend_strong = adx_val >= 25
    above_50ema = last_close > last_ema50
    above_20ema = last_close > last_ema20

    regime: str
    confidence: float
    signal: str
    details: dict[str, float] = {}

    if vol_regime == "panic":
        regime = "panic"
        confidence = min(vol_ratio / 3.0, 1.0)
        signal = "extreme_volatility"
    elif vol_regime == "high":
        regime = "high_volatility"
        confidence = 0.7
        signal = "high_volatility"
    elif trend_strong and above_50ema and above_20ema:
        regime = "bull"
        strength = abs(last_close - last_ema50) / last_ema50 * 100
        confidence = min(strength / 10.0, 1.0)
        signal = "strong_uptrend"
    elif trend_strong and not above_50ema and not above_20ema:
        regime = "bear"
        strength = abs(last_close - last_ema50) / last_ema50 * 100
        confidence = min(strength / 10.0, 1.0)
        signal = "strong_downtrend"
    elif adx_val < 20:
        if rsi_val > 70:
            regime = "bull"
            confidence = 0.4
            signal = "overbought_range"
        elif rsi_val < 30:
            regime = "bear"
            confidence = 0.4
            signal = "oversold_range"
        else:
            regime = "range"
            confidence = 0.6
            signal = "low_trend"
    else:
        regime = "range"
        confidence = 0.5
        signal = "mixed_signals"

    if rsi_val > 70:
        details["overbought"] = rsi_val
    elif rsi_val < 30:
        details["oversold"] = rsi_val

    return RegimeResult(
        regime=regime,
        confidence=round(confidence, 4),
        trend_strength=round(adx_val, 2),
        volatility_regime=vol_regime,
        adx=round(adx_val, 2),
        rsi=round(rsi_val, 2),
        volume_ratio=round(vol_ratio_val, 4),
        signal=signal,
        details=details,
    )
