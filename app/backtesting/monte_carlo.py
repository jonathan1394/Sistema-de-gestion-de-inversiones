"""Monte Carlo simulation for backtest result robustness analysis.

Samples N random paths from the actual trade PnL% distribution
to estimate the range of possible outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from app.backtesting.engine import BacktestResult
from app.backtesting.metrics import BacktestMetrics


@dataclass
class MonteCarloPercentiles:
    p5: float = 0.0
    p50: float = 0.0
    p95: float = 0.0

    @property
    def downside(self) -> float:
        return self.p5

    @property
    def upside(self) -> float:
        return self.p95

    @property
    def median(self) -> float:
        return self.p50


@dataclass
class MonteCarloResult:
    n_simulations: int = 0
    roi_pct: MonteCarloPercentiles = field(default_factory=MonteCarloPercentiles)
    max_drawdown_pct: MonteCarloPercentiles = field(default_factory=MonteCarloPercentiles)
    sharpe_ratio: MonteCarloPercentiles = field(default_factory=MonteCarloPercentiles)
    final_capital: MonteCarloPercentiles = field(default_factory=MonteCarloPercentiles)
    actual_roi_pct: float = 0.0
    actual_max_drawdown_pct: float = 0.0
    actual_sharpe_ratio: float = 0.0
    probability_of_profit: float = 0.0
    probability_of_ruin: float = 0.0
    worst_case_roi_pct: float = 0.0
    best_case_roi_pct: float = 0.0
    all_roi_pct: list[float] = field(default_factory=list)
    all_max_drawdown_pct: list[float] = field(default_factory=list)
    all_sharpe_ratio: list[float] = field(default_factory=list)

    @property
    def summary(self) -> dict:
        return {
            "n_simulations": self.n_simulations,
            "actual_roi_pct": round(self.actual_roi_pct, 4),
            "actual_sharpe": round(self.actual_sharpe_ratio, 4),
            "roi_p50": round(self.roi_pct.p50, 4),
            "roi_p5": round(self.roi_pct.p5, 4),
            "roi_p95": round(self.roi_pct.p95, 4),
            "dd_p50": round(self.max_drawdown_pct.p50, 4),
            "dd_p5": round(self.max_drawdown_pct.p5, 4),
            "sharpe_p50": round(self.sharpe_ratio.p50, 4),
            "prob_profit": round(self.probability_of_profit, 4),
            "prob_ruin": round(self.probability_of_ruin, 4),
            "worst_roi": round(self.worst_case_roi_pct, 4),
            "best_roi": round(self.best_case_roi_pct, 4),
        }


def _compute_metrics_from_pnl_list(
    pnl_pcts: list[float],
    initial_capital: float,
    annualization_factor: float,
    total_bars: int,
) -> BacktestMetrics:
    equity = initial_capital
    curve = [equity]
    for pnl in pnl_pcts:
        equity *= 1 + pnl / 100
        curve.append(equity)

    equity_series = pd.Series(curve)

    peak = equity_series.cummax()
    dd = (peak - equity_series) / peak * 100
    max_dd = float(dd.max())

    final_cap = float(equity_series.iloc[-1])
    roi = (final_cap / initial_capital - 1) * 100

    returns = equity_series.pct_change().dropna()
    if len(returns) > 0 and returns.std() > 0:
        sharpe = float(returns.mean() / returns.std() * np.sqrt(annualization_factor))
    else:
        sharpe = 0.0

    wins = sum(1 for p in pnl_pcts if p > 0)
    losses = sum(1 for p in pnl_pcts if p < 0)
    total = len(pnl_pcts)
    win_rate = wins / total * 100 if total > 0 else 0.0

    avg_win = np.mean([p for p in pnl_pcts if p > 0]) if wins > 0 else 0.0
    avg_loss = abs(np.mean([p for p in pnl_pcts if p < 0])) if losses > 0 else 0.0
    profit_factor = (
        (avg_win * wins) / (avg_loss * losses) if losses > 0 and avg_loss > 0 else float("inf")
    )

    return BacktestMetrics(
        roi_pct=round(roi, 4),
        max_drawdown_pct=round(max_dd, 4),
        sharpe_ratio=round(sharpe, 4),
        win_rate=round(win_rate, 4),
        profit_factor=round(profit_factor, 4),
        total_trades=total,
        winning_trades=wins,
        losing_trades=losses,
        final_capital=round(final_cap, 2),
        initial_capital=initial_capital,
    )


def monte_carlo_simulate(
    backtest_result: BacktestResult,
    n_simulations: int = 1000,
    seed: Optional[int] = None,
) -> MonteCarloResult:
    """Run Monte Carlo simulation on a backtest result.

    Resamples the trade PnL% distribution with replacement to generate
    N random equity paths, then reports percentile statistics.

    Args:
        backtest_result: A completed backtest result.
        n_simulations: Number of random paths to generate.
        seed: Random seed for reproducibility.

    Returns:
        MonteCarloResult with percentile distributions.
    """
    trades = [t for t in backtest_result.trades if t.status == "closed"]
    if not trades:
        return MonteCarloResult(n_simulations=0)

    pnl_pcts = [t.pnl_pct * 100 for t in trades]
    initial_capital = backtest_result.initial_capital

    interval_map = {
        "1m": 525600,
        "5m": 105120,
        "15m": 35040,
        "30m": 17520,
        "1h": 8760,
        "2h": 4380,
        "4h": 2190,
        "6h": 1460,
        "12h": 730,
        "1d": 365,
        "1w": 52,
    }
    annualization_factor = interval_map.get(backtest_result.interval, 365)
    total_bars = len(pnl_pcts)

    rng = np.random.default_rng(seed)

    all_metrics: list[BacktestMetrics] = []
    for _ in range(n_simulations):
        sampled = list(rng.choice(pnl_pcts, size=len(pnl_pcts), replace=True))
        metrics = _compute_metrics_from_pnl_list(
            sampled,
            initial_capital,
            annualization_factor,
            total_bars,
        )
        all_metrics.append(metrics)

    roi_vals = [m.roi_pct for m in all_metrics]
    dd_vals = [m.max_drawdown_pct for m in all_metrics]
    sharpe_vals = [m.sharpe_ratio for m in all_metrics]
    capital_vals = [m.final_capital for m in all_metrics]

    return MonteCarloResult(
        n_simulations=n_simulations,
        roi_pct=MonteCarloPercentiles(
            p5=round(float(np.percentile(roi_vals, 5)), 4),
            p50=round(float(np.percentile(roi_vals, 50)), 4),
            p95=round(float(np.percentile(roi_vals, 95)), 4),
        ),
        max_drawdown_pct=MonteCarloPercentiles(
            p5=round(float(np.percentile(dd_vals, 5)), 4),
            p50=round(float(np.percentile(dd_vals, 50)), 4),
            p95=round(float(np.percentile(dd_vals, 95)), 4),
        ),
        sharpe_ratio=MonteCarloPercentiles(
            p5=round(float(np.percentile(sharpe_vals, 5)), 4),
            p50=round(float(np.percentile(sharpe_vals, 50)), 4),
            p95=round(float(np.percentile(sharpe_vals, 95)), 4),
        ),
        final_capital=MonteCarloPercentiles(
            p5=round(float(np.percentile(capital_vals, 5)), 2),
            p50=round(float(np.percentile(capital_vals, 50)), 2),
            p95=round(float(np.percentile(capital_vals, 95)), 2),
        ),
        actual_roi_pct=round((sum(pnl_pcts) / len(pnl_pcts)) if pnl_pcts else 0.0, 4),
        actual_max_drawdown_pct=round(abs(min(pnl_pcts)) if pnl_pcts else 0.0, 4),
        actual_sharpe_ratio=round(
            (np.mean(pnl_pcts) / np.std(pnl_pcts) * np.sqrt(len(pnl_pcts)))
            if len(pnl_pcts) > 1 and np.std(pnl_pcts) > 0
            else 0.0,
            4,
        ),
        probability_of_profit=round(sum(1 for v in roi_vals if v > 0) / n_simulations, 4),
        probability_of_ruin=round(sum(1 for v in capital_vals if v <= 0) / n_simulations, 4),
        worst_case_roi_pct=round(float(min(roi_vals)), 4),
        best_case_roi_pct=round(float(max(roi_vals)), 4),
        all_roi_pct=roi_vals,
        all_max_drawdown_pct=dd_vals,
        all_sharpe_ratio=sharpe_vals,
    )
