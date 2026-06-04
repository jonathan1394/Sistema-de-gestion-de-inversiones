"""Tests for market regime classifier (app/ai/market_regime.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.ai.market_regime import (
    REGIME_LABELS,
    RegimeResult,
    classify_regime,
)


@pytest.fixture
def _bull_frame() -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="h")
    close = 100 * np.exp(np.cumsum(np.random.normal(0.002, 0.006, 100)))
    return pd.DataFrame(
        {
            "open": close * 0.999,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": np.random.randint(1000, 5000, 100),
        },
        index=dates,
    )


@pytest.fixture
def _bear_frame() -> pd.DataFrame:
    np.random.seed(0)
    dates = pd.date_range("2024-01-01", periods=100, freq="h")
    close = 100 * np.exp(np.cumsum(np.random.normal(-0.003, 0.006, 100)))
    return pd.DataFrame(
        {
            "open": close * 1.001,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": np.random.randint(1000, 5000, 100),
        },
        index=dates,
    )


@pytest.fixture
def _range_frame() -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="h")
    wiggles = np.sin(np.linspace(0, 30 * np.pi, 100)) * 0.1
    noise = np.random.normal(0, 0.03, 100).cumsum() * 0.3
    close = 100.0 + wiggles + noise
    high = close + 0.2 + np.random.uniform(0, 0.2, 100)
    low = close - 0.2 - np.random.uniform(0, 0.2, 100)
    return pd.DataFrame(
        {
            "open": close - 0.05,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.full(100, 2000),
        },
        index=dates,
    )


@pytest.fixture
def _high_vol_frame() -> pd.DataFrame:
    np.random.seed(5)
    dates = pd.date_range("2024-01-01", periods=100, freq="h")
    low_vol = np.random.normal(0, 0.003, 80)
    high_vol = np.random.normal(0, 0.025, 20)
    returns = np.concatenate([low_vol, high_vol])
    close = 100 * np.exp(np.cumsum(returns))
    return pd.DataFrame(
        {
            "open": close * 0.998,
            "high": close * 1.02,
            "low": close * 0.98,
            "close": close,
            "volume": np.random.randint(2000, 10000, 100),
        },
        index=dates,
    )


class TestClassifyRegime:
    def test_bull_regime(self, _bull_frame):
        result = classify_regime(_bull_frame)
        assert result.regime == "bull"
        assert result.confidence > 0
        assert result.adx > 0
        assert isinstance(result, RegimeResult)

    def test_bear_regime(self, _bear_frame):
        result = classify_regime(_bear_frame)
        assert result.regime == "bear"
        assert result.confidence > 0

    def test_range_regime(self, _range_frame):
        result = classify_regime(_range_frame)
        assert result.regime == "range"

    def test_high_volatility_regime(self, _high_vol_frame):
        result = classify_regime(_high_vol_frame)
        assert result.regime in ("high_volatility", "panic")

    def test_regime_field_types(self, _bull_frame):
        result = classify_regime(_bull_frame)
        assert isinstance(result.regime, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.trend_strength, float)
        assert isinstance(result.adx, float)
        assert isinstance(result.rsi, float)
        assert isinstance(result.volume_ratio, float)
        assert isinstance(result.signal, str)

    def test_regime_in_valid_set(self, _bull_frame):
        result = classify_regime(_bull_frame)
        assert result.regime in REGIME_LABELS

    def test_empty_dataframe_raises(self):
        with pytest.raises(ValueError, match="No data provided"):
            classify_regime(pd.DataFrame())

    def test_timestamp_column_conversion(self):
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=50, freq="h"),
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100.5,
                "volume": 1000,
            }
        )
        result = classify_regime(df)
        assert isinstance(result, RegimeResult)

    def test_minimal_data(self):
        df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [101, 102, 103],
                "low": [99, 100, 101],
                "close": [100, 101, 102],
            }
        )
        result = classify_regime(df)
        assert isinstance(result, RegimeResult)
        assert result.confidence >= 0

    def test_panic_volatility(self):
        np.random.seed(5)
        dates = pd.date_range("2024-01-01", periods=100, freq="h")
        returns = np.random.normal(0, 0.05, 100)
        close = 100 * np.exp(np.cumsum(returns))
        df = pd.DataFrame(
            {
                "open": close * 0.995,
                "high": close * 1.03,
                "low": close * 0.97,
                "close": close,
                "volume": np.random.randint(5000, 20000, 100),
            },
            index=dates,
        )
        result = classify_regime(df)
        assert result.regime in REGIME_LABELS

    def test_details_overbought(self):
        np.random.seed(6)
        dates = pd.date_range("2024-01-01", periods=60, freq="h")
        close = 100 + np.linspace(0, 15, 60) + np.random.normal(0, 0.5, 60)
        df = pd.DataFrame(
            {"open": close - 0.2, "high": close + 0.5, "low": close - 0.5, "close": close},
            index=dates,
        )
        result = classify_regime(df)
        assert isinstance(result.details, dict)


class TestRegimeResult:
    def test_dataclass_defaults(self):
        r = RegimeResult(
            regime="bull",
            confidence=0.8,
            trend_strength=30.0,
            volatility_regime="normal",
            adx=30.0,
            rsi=55.0,
            volume_ratio=1.0,
            signal="strong_uptrend",
        )
        assert r.regime == "bull"
        assert r.confidence == 0.8
        assert r.details == {}

    def test_regime_labels_constant(self):
        assert "bull" in REGIME_LABELS
        assert "bear" in REGIME_LABELS
        assert "range" in REGIME_LABELS
        assert "high_volatility" in REGIME_LABELS
        assert "panic" in REGIME_LABELS
        assert len(REGIME_LABELS) == 5


class TestClassifyRegimeEdgeCases:
    def test_no_volume_column(self):
        df = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [101, 102, 103],
                "low": [99, 100, 101],
                "close": [100.5, 101.5, 102.5],
            }
        )
        result = classify_regime(df)
        assert result.volume_ratio == 1.0
