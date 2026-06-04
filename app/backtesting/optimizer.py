"""Walk-forward optimization for strategy parameter validation.

Divides data into N windows (train/test), optimizes parameters on each
train window, evaluates on the corresponding test window, and aggregates
results to reduce overfitting risk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any, Optional

import pandas as pd

from app.backtesting.engine import BacktestEngine, BacktestResult
from app.backtesting.metrics import BacktestMetrics, compute_metrics
from app.strategies.base_strategy import BaseStrategy


@dataclass
class ParamGrid:
    """Defines a search space for one strategy parameter."""

    name: str
    values: list


@dataclass
class WalkForwardWindow:
    """Results for one train/test window pair."""

    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    best_params: dict[str, Any]
    train_metrics: BacktestMetrics
    test_metrics: BacktestMetrics
    train_result: BacktestResult
    test_result: BacktestResult


@dataclass
class WalkForwardResult:
    """Aggregated walk-forward optimization results."""

    windows: list[WalkForwardWindow] = field(default_factory=list)
    strategy_name: str = ""
    total_windows: int = 0
    avg_train_metrics: Optional[BacktestMetrics] = None
    avg_test_metrics: Optional[BacktestMetrics] = None
    consistency_score: float = 0.0
    best_params_overall: dict[str, Any] = field(default_factory=dict)

    @property
    def summary(self) -> dict:
        return {
            "strategy": self.strategy_name,
            "windows": self.total_windows,
            "consistency_score": round(self.consistency_score, 4),
            "best_params_overall": self.best_params_overall,
            "avg_train_sharpe": round(self.avg_train_metrics.sharpe_ratio, 4)
            if self.avg_train_metrics
            else None,
            "avg_test_sharpe": round(self.avg_test_metrics.sharpe_ratio, 4)
            if self.avg_test_metrics
            else None,
            "avg_train_roi_pct": round(self.avg_train_metrics.roi_pct, 4)
            if self.avg_train_metrics
            else None,
            "avg_test_roi_pct": round(self.avg_test_metrics.roi_pct, 4)
            if self.avg_test_metrics
            else None,
            "avg_train_trades": self.avg_train_metrics.total_trades
            if self.avg_train_metrics
            else None,
            "avg_test_trades": self.avg_test_metrics.total_trades
            if self.avg_test_metrics
            else None,
        }


def _build_param_combinations(param_grid: list[ParamGrid]) -> list[dict]:
    keys = [p.name for p in param_grid]
    value_lists = [p.values for p in param_grid]
    return [dict(zip(keys, combo)) for combo in product(*value_lists)]


def _run_single_backtest(
    data: pd.DataFrame,
    strategy: BaseStrategy,
    initial_capital: float,
    commission_pct: float,
    slippage_pct: float,
    symbol: str,
    interval: str,
) -> tuple[BacktestResult, BacktestMetrics]:
    engine = BacktestEngine(
        strategy=strategy,
        data=data,
        initial_capital=initial_capital,
        commission_pct=commission_pct,
        slippage_pct=slippage_pct,
        symbol=symbol,
        interval=interval,
    )
    result = engine.run()
    metrics = compute_metrics(result)
    return result, metrics


def _pick_best_params(
    param_results: list[tuple[dict, BacktestMetrics]],
    optimize_metric: str,
) -> dict:
    best = param_results[0]
    best_val = getattr(best[1], optimize_metric, -float("inf"))
    for params, metrics in param_results[1:]:
        val = getattr(metrics, optimize_metric, -float("inf"))
        if val > best_val:
            best_val = val
            best = (params, metrics)
    return best[0]


def walk_forward_optimize(
    strategy_class: type[BaseStrategy],
    param_grid: list[ParamGrid],
    data: pd.DataFrame,
    symbol: str = "UNKNOWN",
    interval: str = "1h",
    n_windows: int = 3,
    train_pct: float = 0.7,
    initial_capital: float = 1000.0,
    commission_pct: float = 0.001,
    slippage_pct: float = 0.001,
    optimize_metric: str = "sharpe_ratio",
) -> WalkForwardResult:
    """Run walk-forward optimization for a strategy parameter grid.

    Args:
        strategy_class: Strategy class (not instance).
        param_grid: List of parameter search spaces.
        data: OHLCV DataFrame with 'timestamp' column or DatetimeIndex.
        symbol: Trading symbol label.
        interval: Bar interval label.
        n_windows: Number of train/test windows.
        train_pct: Fraction of each window used for training.
        initial_capital: Capital for each backtest.
        commission_pct: Trading commission.
        slippage_pct: Slippage per trade.
        optimize_metric: Metric name from BacktestMetrics to optimize.

    Returns:
        WalkForwardResult with per-window and aggregated metrics.
    """
    if "timestamp" in data.columns:
        data = data.set_index("timestamp")
    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index)
    data = data.sort_index()

    idx = data.index
    total_bars = len(idx)
    window_size = total_bars // n_windows
    train_bars = int(window_size * train_pct)

    param_combos = _build_param_combinations(param_grid)
    windows: list[WalkForwardWindow] = []
    all_train_results: list[BacktestMetrics] = []
    all_test_results: list[BacktestMetrics] = []

    for w in range(n_windows):
        w_start = w * window_size
        w_mid = w_start + train_bars
        w_end = min(w_start + window_size, total_bars)

        if w_start >= total_bars or w_mid >= total_bars:
            break

        train_slice = data.iloc[w_start:w_mid]
        test_slice = data.iloc[w_mid:w_end]

        if len(train_slice) < 50 or len(test_slice) < 20:
            continue

        if not param_combos:
            param_combos = [{}]

        param_scores: list[tuple[dict, BacktestMetrics]] = []
        for combo in param_combos:
            params = {"symbol": symbol, **combo}
            strategy = strategy_class(parameters=params)
            _, metrics = _run_single_backtest(
                train_slice,
                strategy,
                initial_capital,
                commission_pct,
                slippage_pct,
                symbol,
                interval,
            )
            param_scores.append((combo, metrics))

        best_params = _pick_best_params(param_scores, optimize_metric)

        train_params = {"symbol": symbol, **best_params}
        train_strategy = strategy_class(parameters=train_params)
        train_result, train_metrics = _run_single_backtest(
            train_slice,
            train_strategy,
            initial_capital,
            commission_pct,
            slippage_pct,
            symbol,
            interval,
        )

        test_params = {"symbol": symbol, **best_params}
        test_strategy = strategy_class(parameters=test_params)
        test_result, test_metrics = _run_single_backtest(
            test_slice,
            test_strategy,
            initial_capital,
            commission_pct,
            slippage_pct,
            symbol,
            interval,
        )

        windows.append(
            WalkForwardWindow(
                train_start=train_slice.index[0],
                train_end=train_slice.index[-1],
                test_start=test_slice.index[0],
                test_end=test_slice.index[-1],
                best_params=best_params,
                train_metrics=train_metrics,
                test_metrics=test_metrics,
                train_result=train_result,
                test_result=test_result,
            )
        )
        all_train_results.append(train_metrics)
        all_test_results.append(test_metrics)

    if not windows:
        return WalkForwardResult(strategy_name=strategy_class.__name__)

    avg_train = _average_metrics(all_train_results, initial_capital)
    avg_test = _average_metrics(all_test_results, initial_capital)

    positive_test_sharpes = sum(1 for m in all_test_results if m.sharpe_ratio > 0)
    consistency = positive_test_sharpes / len(all_test_results) if all_test_results else 0.0

    param_freq: dict[str, dict] = {}
    for w in windows:
        for k, v in w.best_params.items():
            param_freq.setdefault(k, {})
            param_freq[k][str(v)] = param_freq[k].get(str(v), 0) + 1
    best_overall = {}
    for k, freq in param_freq.items():
        best_overall[k] = max(freq, key=freq.get)

    return WalkForwardResult(
        windows=windows,
        strategy_name=strategy_class.__name__,
        total_windows=len(windows),
        avg_train_metrics=avg_train,
        avg_test_metrics=avg_test,
        consistency_score=consistency,
        best_params_overall=best_overall,
    )


def _average_metrics(
    metrics_list: list[BacktestMetrics], initial_capital: float
) -> BacktestMetrics:
    n = len(metrics_list)
    if n == 0:
        return BacktestMetrics()
    avg = BacktestMetrics()
    for key in [
        "roi_pct",
        "cagr_pct",
        "max_drawdown_pct",
        "sharpe_ratio",
        "sortino_ratio",
        "win_rate",
        "profit_factor",
        "expectancy",
        "total_trades",
        "winning_trades",
        "losing_trades",
        "avg_win_pct",
        "avg_loss_pct",
        "payoff_ratio",
        "avg_hold_bars",
        "total_fees",
        "gross_profit",
        "gross_loss",
        "largest_win_pct",
        "largest_loss_pct",
        "consecutive_wins",
        "consecutive_losses",
        "time_in_market_pct",
    ]:
        vals = [getattr(m, key, 0) for m in metrics_list]
        setattr(avg, key, sum(vals) / n)

    avg.initial_capital = initial_capital
    avg.final_capital = initial_capital * (1 + avg.roi_pct / 100)
    return avg
