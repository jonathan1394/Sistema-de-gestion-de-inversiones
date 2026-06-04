"""Candlestick pattern detection for common reversal and continuation patterns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class PatternResult:
    pattern: str
    direction: str  # "bullish", "bearish", "neutral"
    confidence: float  # 0.0 to 1.0
    timestamp: Optional[pd.Timestamp] = None


def _body_length(df: pd.DataFrame) -> pd.Series:
    return (df["close"] - df["open"]).abs()


def _upper_wick(df: pd.DataFrame) -> pd.Series:
    return df["high"] - df[["close", "open"]].max(axis=1)


def _lower_wick(df: pd.DataFrame) -> pd.Series:
    return df[["close", "open"]].min(axis=1) - df["low"]


def _total_range(df: pd.DataFrame) -> pd.Series:
    return df["high"] - df["low"]


def detect_doji(df: pd.DataFrame, tolerance: float = 0.05) -> pd.Series:
    """Detect doji candles where body is very small relative to total range."""
    total = _total_range(df)
    body = _body_length(df)
    doji = (body <= total * tolerance) & (total > 0)
    return pd.Series(doji, index=df.index)


def detect_hammer(df: pd.DataFrame, body_to_wick_ratio: float = 2.0) -> pd.Series:
    """Detect hammer pattern: small body at top, long lower wick."""
    body = _body_length(df)
    lower = _lower_wick(df)
    upper = _upper_wick(df)
    total = _total_range(df)
    is_hit = (
        (lower >= body * body_to_wick_ratio)
        & (upper <= body * 0.3)
        & (df["close"] > df["open"])  # green candle
        & (total > 0)
    )
    return pd.Series(is_hit, index=df.index)


def detect_shooting_star(df: pd.DataFrame, body_to_wick_ratio: float = 2.0) -> pd.Series:
    """Detect shooting star: small body at bottom, long upper wick."""
    body = _body_length(df)
    upper = _upper_wick(df)
    lower = _lower_wick(df)
    total = _total_range(df)
    is_hit = (
        (upper >= body * body_to_wick_ratio)
        & (lower <= body * 0.3)
        & (df["close"] < df["open"])  # red candle
        & (total > 0)
    )
    return pd.Series(is_hit, index=df.index)


def detect_engulfing(df: pd.DataFrame) -> pd.Series:
    """Detect bullish/bearish engulfing patterns across consecutive candles."""
    if len(df) < 2:
        return pd.Series([False] * len(df), index=df.index)

    prev_close = df["close"].shift(1)
    prev_open = df["open"].shift(1)
    prev_body = abs(prev_close - prev_open)
    curr_open = df["open"]
    curr_close = df["close"]

    bull_eng = (
        (prev_close < prev_open)  # prev is red
        & (curr_close > curr_open)  # curr is green
        & (curr_open < prev_close)  # opens below prev close
        & (curr_close > prev_open)  # closes above prev open
        & (prev_body > 0)
    )

    bear_eng = (
        (prev_close > prev_open)  # prev is green
        & (curr_close < curr_open)  # curr is red
        & (curr_open > prev_close)  # opens above prev close
        & (curr_close < prev_open)  # closes below prev open
        & (prev_body > 0)
    )

    return pd.Series(bull_eng | bear_eng, index=df.index).fillna(False)


def detect_three_white_soldiers(df: pd.DataFrame) -> pd.Series:
    """Detect three consecutive long green candles with higher closes."""
    if len(df) < 3:
        return pd.Series([False] * len(df), index=df.index)

    green = df["close"] > df["open"]
    body = _body_length(df)
    avg_body = body.rolling(10, min_periods=1).mean()

    long_green = green & (body > avg_body * 0.8)

    prev_close = df["close"].shift(1)
    higher_close = prev_close.isna() | (df["close"] > prev_close)

    pattern = long_green & higher_close
    result = pattern.rolling(3).sum() >= 3
    return pd.Series(result, index=df.index).fillna(False)


def detect_three_black_crows(df: pd.DataFrame) -> pd.Series:
    """Detect three consecutive long red candles with lower closes."""
    if len(df) < 3:
        return pd.Series([False] * len(df), index=df.index)

    red = df["close"] < df["open"]
    body = _body_length(df)
    avg_body = body.rolling(10, min_periods=1).mean()

    long_red = red & (body > avg_body * 0.8)

    prev_close = df["close"].shift(1)
    lower_close = prev_close.isna() | (df["close"] < prev_close)

    pattern = long_red & lower_close
    result = pattern.rolling(3).sum() >= 3
    return pd.Series(result, index=df.index).fillna(False)


def detect_all_patterns(df: pd.DataFrame) -> list[PatternResult]:
    """Run all pattern detectors and return a consolidated list of results."""
    if df.empty or "open" not in df.columns:
        return []

    results: list[PatternResult] = []
    detectors = {
        "doji": (detect_doji(df), "neutral", 0.3),
        "hammer": (detect_hammer(df), "bullish", 0.6),
        "shooting_star": (detect_shooting_star(df), "bearish", 0.6),
        "engulfing": (detect_engulfing(df), "neutral", 0.7),
        "three_white_soldiers": (detect_three_white_soldiers(df), "bullish", 0.8),
        "three_black_crows": (detect_three_black_crows(df), "bearish", 0.8),
    }

    for name, (series, direction, confidence) in detectors.items():
        hits = series[series]
        for ts in hits.index:
            results.append(
                PatternResult(
                    pattern=name,
                    direction=direction,
                    confidence=confidence,
                    timestamp=pd.Timestamp(ts),
                )
            )

    return results
