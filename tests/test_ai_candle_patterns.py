"""Tests for candlestick pattern detection (app/ai/candle_patterns.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.ai.candle_patterns import (
    PatternResult,
    detect_all_patterns,
    detect_doji,
    detect_engulfing,
    detect_hammer,
    detect_shooting_star,
    detect_three_black_crows,
    detect_three_white_soldiers,
)


def _candle(open_, high, low, close):
    return pd.DataFrame(
        {"open": [open_], "high": [high], "low": [low], "close": [close]}
    )


def _candles(data: list[tuple]) -> pd.DataFrame:
    df = pd.DataFrame(data, columns=["open", "high", "low", "close"])
    df.index = pd.date_range("2024-01-01", periods=len(df), freq="h")
    return df


class TestDoji:
    def test_doji_detected(self):
        df = _candle(100, 102, 98, 100.1)
        assert detect_doji(df).iloc[0]

    def test_long_body_not_doji(self):
        df = _candle(100, 110, 90, 108)
        assert not detect_doji(df).iloc[0]

    def test_zero_range_not_doji(self):
        df = _candle(100, 100, 100, 100)
        assert not detect_doji(df).iloc[0]


class TestHammer:
    def test_hammer_detected(self):
        df = _candle(100, 101, 95, 101)
        assert detect_hammer(df).iloc[0]

    def test_red_candle_not_hammer(self):
        df = _candle(100, 101, 95, 99)
        assert not detect_hammer(df).iloc[0]

    def test_no_lower_wick_not_hammer(self):
        df = _candle(100, 103, 99, 102)
        assert not detect_hammer(df).iloc[0]


class TestShootingStar:
    def test_shooting_star_detected(self):
        df = _candle(101, 107, 100, 100)
        assert detect_shooting_star(df).iloc[0]

    def test_green_candle_not_shooting_star(self):
        df = _candle(101, 107, 100, 105)
        assert not detect_shooting_star(df).iloc[0]

    def test_no_upper_wick_not_shooting_star(self):
        df = _candle(100, 101, 98, 99)
        assert not detect_shooting_star(df).iloc[0]


class TestEngulfing:
    def test_bullish_engulfing(self):
        df = _candles([(105, 107, 103, 104), (103, 109, 102, 108)])
        assert detect_engulfing(df).iloc[-1]

    def test_bearish_engulfing(self):
        df = _candles([(100, 103, 99, 102), (104, 106, 99, 99)])
        assert detect_engulfing(df).iloc[-1]

    def test_no_engulfing(self):
        df = _candles([(100, 103, 98, 102), (102, 105, 100, 104)])
        assert not detect_engulfing(df).iloc[-1]

    def test_insufficient_data(self):
        df = _candle(100, 105, 95, 102)
        assert not detect_engulfing(df).iloc[0]


class TestThreeWhiteSoldiers:
    def test_detected(self):
        df = _candles([(100, 103, 99, 102), (103, 107, 102, 106), (107, 112, 106, 111)])
        result = detect_three_white_soldiers(df)
        assert result.iloc[-1]

    def test_red_candles_not_detected(self):
        df = _candles([(102, 105, 100, 101), (101, 104, 99, 100), (100, 103, 98, 99)])
        assert not detect_three_white_soldiers(df).iloc[-1]


class TestThreeBlackCrows:
    def test_detected(self):
        df = _candles([(105, 107, 102, 102), (102, 105, 99, 99), (99, 101, 96, 96)])
        result = detect_three_black_crows(df)
        assert result.iloc[-1]

    def test_green_candles_not_detected(self):
        df = _candles([(100, 103, 99, 102), (102, 106, 101, 105), (105, 109, 104, 108)])
        assert not detect_three_black_crows(df).iloc[-1]


class TestDetectAll:
    def test_returns_list_of_pattern_results(self):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        close = 100 + np.cumsum(np.random.normal(0, 0.5, 100))
        df = pd.DataFrame(
            {
                "open": close - 0.2,
                "high": close + 0.5,
                "low": close - 0.5,
                "close": close,
            },
            index=dates,
        )
        results = detect_all_patterns(df)
        assert isinstance(results, list)
        if results:
            r = results[0]
            assert isinstance(r, PatternResult)
            assert r.pattern in (
                "doji", "hammer", "shooting_star", "engulfing",
                "three_white_soldiers", "three_black_crows",
            )
            assert r.direction in ("bullish", "bearish", "neutral")

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        assert detect_all_patterns(df) == []

    def test_missing_columns(self):
        df = pd.DataFrame({"close": [100, 101]})
        assert detect_all_patterns(df) == []


class TestPatternResult:
    def test_dataclass_fields(self):
        r = PatternResult(pattern="doji", direction="neutral", confidence=0.3)
        assert r.pattern == "doji"
        assert r.direction == "neutral"
        assert r.confidence == 0.3
        assert r.timestamp is None
