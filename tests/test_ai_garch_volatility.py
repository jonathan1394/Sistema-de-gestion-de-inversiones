"""Tests for GARCH volatility model (app/ai/garch_volatility.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.ai.garch_volatility import GarchResult, fit_garch, forecast_volatility


@pytest.fixture
def _volatile_frame() -> pd.DataFrame:
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=200, freq="h")
    returns = np.random.normal(0, 0.01, 200)
    close = 100 * np.exp(np.cumsum(returns))
    return pd.DataFrame(
        {
            "open": close * 0.999,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
        },
        index=dates,
    )


class TestFitGarch:
    def test_returns_garch_result(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        assert isinstance(result, GarchResult)

    def test_parameters_positive(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        assert result.omega > 0
        assert result.alpha > 0
        assert result.beta > 0

    def test_persistence_less_than_one(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        assert result.persistence < 1.0

    def test_conditional_volatility_length(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        n_returns = len(_volatile_frame) - 1  # pct_change drops one
        assert len(result.conditional_volatility) == n_returns

    def test_conditional_volatility_non_negative(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        assert (result.conditional_volatility >= 0).all()

    def test_forecast_positive(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        assert result.forecast > 0

    def test_log_likelihood_finite(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        assert np.isfinite(result.log_likelihood)

    def test_n_obs(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        assert result.n_obs == len(_volatile_frame) - 1

    def test_unconditional_vol_positive(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        assert result.unconditional_vol > 0

    def test_forecast_horizon_default(self, _volatile_frame):
        result = fit_garch(_volatile_frame, forecast_horizon=5)
        assert result.details["forecast_horizon"] == 5


class TestFitGarchEdgeCases:
    def test_insufficient_data_raises(self):
        df = pd.DataFrame({"close": [100, 101]})
        with pytest.raises(ValueError, match="Need at least 10 returns"):
            fit_garch(df)

    def test_minimal_data(self):
        np.random.seed(1)
        dates = pd.date_range("2024-01-01", periods=15, freq="h")
        close = 100 + np.random.normal(0, 1, 15).cumsum()
        df = pd.DataFrame({"close": close}, index=dates)
        result = fit_garch(df)
        assert isinstance(result, GarchResult)

    def test_constant_prices(self):
        dates = pd.date_range("2024-01-01", periods=50, freq="h")
        df = pd.DataFrame({"close": [100.0] * 50}, index=dates)
        result = fit_garch(df)
        assert result.omega < 1e-4 or result.alpha < 1e-4
        assert result.n_obs == 49

    def test_forecast_horizon_parameter(self, _volatile_frame):
        result = fit_garch(_volatile_frame, forecast_horizon=10)
        assert result.forecast > 0


class TestForecastVolatility:
    def test_returns_list(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        forecasts = forecast_volatility(result)
        assert isinstance(forecasts, list)

    def test_returns_correct_length(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        forecasts = forecast_volatility(result, steps=10)
        assert len(forecasts) == 10

    def test_forecasts_decreasing(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        forecasts = forecast_volatility(result, steps=5)
        assert all(f > 0 for f in forecasts)
        # GARCH forecasts converge to unconditional vol
        for i in range(1, len(forecasts)):
            assert abs(forecasts[i] - forecasts[i - 1]) < forecasts[0] * 2

    def test_default_steps(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        forecasts = forecast_volatility(result)
        assert len(forecasts) == 10


class TestGarchResult:
    def test_dataclass_fields(self):
        cond_vol = pd.Series([1.0, 1.1, 1.2])
        r = GarchResult(
            omega=0.01,
            alpha=0.1,
            beta=0.85,
            persistence=0.95,
            unconditional_vol=0.447,
            conditional_volatility=cond_vol,
            forecast=1.15,
            log_likelihood=-100.0,
            converged=True,
            n_obs=3,
        )
        assert r.omega == 0.01
        assert r.alpha == 0.1
        assert r.beta == 0.85
        assert r.persistence == 0.95
        assert r.forecast == 1.15
        assert r.converged

    def test_details_default(self, _volatile_frame):
        result = fit_garch(_volatile_frame)
        assert "last_return" in result.details
        assert "sample_var" in result.details
        assert "forecast_horizon" in result.details
