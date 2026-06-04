"""GARCH(1,1) volatility model for conditional volatility estimation."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import minimize


@dataclass
class GarchResult:
    """Result of GARCH(1,1) model estimation."""

    omega: float
    alpha: float
    beta: float
    persistence: float
    unconditional_vol: float
    conditional_volatility: pd.Series
    forecast: float
    log_likelihood: float
    converged: bool
    n_obs: int
    details: dict[str, float] = field(default_factory=dict)


def _garch_likelihood(
    params: np.ndarray, returns: np.ndarray
) -> float:
    """Negative log-likelihood for GARCH(1,1)."""
    omega, alpha, beta = params
    n = len(returns)
    var0 = omega / max(1 - alpha - beta, 1e-12)
    sigma2 = np.full(n, var0)
    for t in range(1, n):
        sigma2[t] = omega + alpha * returns[t - 1] ** 2 + beta * sigma2[t - 1]
    sigma2 = np.maximum(sigma2, 1e-12)
    neg_ll = 0.5 * n * np.log(2 * np.pi)
    neg_ll += 0.5 * np.sum(np.log(sigma2))
    neg_ll += 0.5 * np.sum(returns**2 / sigma2)
    return neg_ll


def _estimate_garch(
    returns: np.ndarray,
    max_iter: int = 500,
) -> tuple[float, float, float, float, bool]:
    """Estimate GARCH(1,1) parameters via MLE."""
    n = len(returns)
    init_var = float(np.var(returns)) if n > 0 else 1.0
    omega0 = init_var * 0.1
    alpha0 = 0.1
    beta0 = 0.8

    bounds = [
        (1e-8, None),
        (1e-8, 1 - 1e-8),
        (1e-8, 1 - 1e-8),
    ]

    constraints = [{"type": "ineq", "fun": lambda x: 1 - x[1] - x[2]}]

    result = minimize(
        _garch_likelihood,
        x0=[omega0, alpha0, beta0],
        args=(returns,),
        bounds=bounds,
        constraints=constraints,
        method="SLSQP",
        options={"maxiter": max_iter, "ftol": 1e-8},
    )

    omega, alpha, beta = result.x
    converged = result.success
    return omega, alpha, beta, float(result.fun), converged


def fit_garch(
    data: pd.DataFrame,
    forecast_horizon: int = 5,
    max_iter: int = 500,
) -> GarchResult:
    """Fit a GARCH(1,1) model to OHLCV data and return volatility estimates.

    Args:
        data: DataFrame with at least a ``close`` column.
        forecast_horizon: Number of steps ahead to forecast volatility.
        max_iter: Maximum iterations for MLE solver.

    Returns:
        GarchResult with estimated parameters and conditional volatility.
    """
    close = data["close"] if "close" in data.columns else data.iloc[:, 0]
    returns = close.pct_change().dropna().values * 100
    if len(returns) < 10:
        raise ValueError(
            f"Need at least 10 returns for GARCH estimation, got {len(returns)}"
        )

    omega, alpha, beta, loglike, converged = _estimate_garch(
        returns, max_iter
    )

    n = len(returns)
    var0 = omega / max(1 - alpha - beta, 1e-12)
    sigma2 = np.full(n, var0)
    for t in range(1, n):
        sigma2[t] = omega + alpha * returns[t - 1] ** 2 + beta * sigma2[t - 1]
    sigma2 = np.maximum(sigma2, 1e-12)
    sigma = np.sqrt(sigma2)

    date_index = (
        close.index[1:]
        if len(close) > len(sigma2)
        else close.index[-len(sigma2):]
    )
    cond_vol = pd.Series(sigma, index=date_index, name="conditional_volatility")

    persistence = alpha + beta
    unconditional_vol = np.sqrt(omega / (1 - persistence)) if persistence < 1 else np.nan

    forecast_var = omega
    for _ in range(forecast_horizon):
        forecast_var = omega + (alpha + beta) * forecast_var
    forecast = np.sqrt(forecast_var)

    return GarchResult(
        omega=omega,
        alpha=alpha,
        beta=beta,
        persistence=persistence,
        unconditional_vol=float(unconditional_vol) if np.isfinite(unconditional_vol) else 0.0,
        conditional_volatility=cond_vol,
        forecast=float(forecast),
        log_likelihood=loglike,
        converged=converged,
        n_obs=n,
        details={
            "last_return": float(returns[-1]) if len(returns) > 0 else 0.0,
            "sample_var": float(np.var(returns)),
            "forecast_horizon": forecast_horizon,
        },
    )


def forecast_volatility(
    garch_result: GarchResult,
    steps: int = 10,
) -> list[float]:
    """Generate a multi-step volatility forecast from a fitted GARCH model."""
    forecast_var = garch_result.forecast**2
    forecasts = [garch_result.forecast]
    for _ in range(steps - 1):
        forecast_var = (
            garch_result.omega
            + (garch_result.alpha + garch_result.beta) * forecast_var
        )
        forecasts.append(float(np.sqrt(forecast_var)))
    return forecasts
