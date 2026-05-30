"""Tools to compare backtest outcomes across strategies and assets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from app.backtesting.engine import BacktestEngine, BacktestResult
from app.backtesting.metrics import BacktestMetrics, compute_metrics
from app.strategies.base_strategy import BaseStrategy
from app.strategies.dca_dynamic import DCADynamic
from app.strategies.moving_average import MovingAverageCrossover
from app.strategies.rebalance import RebalanceStrategy
from app.strategies.rsi_strategy import RSIStrategy
from app.strategies.trend_following import TrendFollowing


@dataclass
class StrategyMetrics:
    strategy_name: str
    parameters: dict
    metrics: BacktestMetrics
    result: BacktestResult
    passed_validation: bool = False


@dataclass
class AssetStrategyResult:
    symbol: str
    interval: str
    strategy_results: list[StrategyMetrics] = field(default_factory=list)

    @property
    def best(self) -> Optional[StrategyMetrics]:
        """Return best valid strategy by Sharpe ratio."""
        valid = [r for r in self.strategy_results if r.passed_validation]
        if not valid:
            return None
        return max(valid, key=lambda r: r.metrics.sharpe_ratio)

    @property
    def ranking(self) -> list[StrategyMetrics]:
        """Return all strategy results sorted by Sharpe ratio."""
        return sorted(
            self.strategy_results,
            key=lambda r: r.metrics.sharpe_ratio,
            reverse=True,
        )


@dataclass
class ConsolidatedRanking:
    entries: list[dict] = field(default_factory=list)

    @property
    def top(self) -> Optional[dict]:
        """Return top consolidated entry if available."""
        return self.entries[0] if self.entries else None

    def to_dataframe(self) -> pd.DataFrame:
        """Convert ranking entries to pandas DataFrame."""
        return pd.DataFrame(self.entries)

    def filter_min_trades(self, min_trades: int) -> ConsolidatedRanking:
        """Filter consolidated entries by minimum trade count."""
        filtered = [e for e in self.entries if e.get("total_trades", 0) >= min_trades]
        return ConsolidatedRanking(entries=filtered)

    def filter_min_sharpe(self, min_sharpe: float) -> ConsolidatedRanking:
        """Filter consolidated entries by minimum Sharpe ratio."""
        filtered = [e for e in self.entries if e.get("sharpe_ratio", 0) >= min_sharpe]
        return ConsolidatedRanking(entries=filtered)


DEFAULT_STRATEGIES: list[BaseStrategy] = [
    MovingAverageCrossover(parameters={"fast_period": 20, "slow_period": 50}),
    RSIStrategy(parameters={"rsi_period": 14, "oversold": 30, "overbought": 70}),
    TrendFollowing(parameters={"ema_long": 200, "ema_fast": 20, "ema_slow": 50}),
    DCADynamic(parameters={"base_investment": 100, "interval_days": 7}),
    RebalanceStrategy(parameters={"target_pct": 0.5, "rebalance_frequency": 30}),
]


def compare_strategies(
    data: pd.DataFrame,
    symbol: str = "UNKNOWN",
    interval: str = "4h",
    initial_capital: float = 1000.0,
    commission_pct: float = 0.001,
    slippage_pct: float = 0.001,
    strategies: Optional[list[BaseStrategy]] = None,
    min_trades: int = 0,
    min_sharpe: float = 0.0,
) -> AssetStrategyResult:
    """Run several strategies on one dataset and collect metrics."""
    if strategies is None:
        strategies = DEFAULT_STRATEGIES

    result = AssetStrategyResult(symbol=symbol, interval=interval)

    for strategy in strategies:
        try:
            engine = BacktestEngine(
                strategy=strategy,
                data=data,
                initial_capital=initial_capital,
                commission_pct=commission_pct,
                slippage_pct=slippage_pct,
                symbol=symbol,
                interval=interval,
            )
            bt_result = engine.run()
            metrics = compute_metrics(bt_result)

            passed = True
            if min_trades > 0 and metrics.total_trades < min_trades:
                passed = False
            if min_sharpe > 0 and metrics.sharpe_ratio < min_sharpe:
                passed = False

            result.strategy_results.append(
                StrategyMetrics(
                    strategy_name=type(strategy).__name__,
                    parameters=getattr(strategy, "parameters", {}),
                    metrics=metrics,
                    result=bt_result,
                    passed_validation=passed,
                )
            )
        except Exception:
            continue

    return result


def compare_across_assets(
    data_by_asset: dict[str, dict[str, pd.DataFrame]],
    initial_capital: float = 1000.0,
    commission_pct: float = 0.001,
    slippage_pct: float = 0.001,
    strategies: Optional[list[BaseStrategy]] = None,
    min_trades: int = 0,
    min_sharpe: float = 0.0,
) -> ConsolidatedRanking:
    """Run strategy comparison across symbols and intervals."""
    if strategies is None:
        strategies = DEFAULT_STRATEGIES

    ranking_entries: list[dict] = []

    for symbol, intervals in data_by_asset.items():
        for interval, data in intervals.items():
            asset_result = compare_strategies(
                data=data,
                symbol=symbol,
                interval=interval,
                initial_capital=initial_capital,
                commission_pct=commission_pct,
                slippage_pct=slippage_pct,
                strategies=strategies,
                min_trades=min_trades,
                min_sharpe=min_sharpe,
            )

            for sr in asset_result.strategy_results:
                m = sr.metrics
                ranking_entries.append({
                    "symbol": symbol,
                    "interval": interval,
                    "strategy": sr.strategy_name,
                    "roi_pct": round(m.roi_pct, 2),
                    "sharpe_ratio": round(m.sharpe_ratio, 2),
                    "sortino_ratio": round(m.sortino_ratio, 2),
                    "max_drawdown_pct": round(m.max_drawdown_pct, 2),
                    "profit_factor": round(m.profit_factor, 2),
                    "win_rate": round(m.win_rate, 1),
                    "total_trades": m.total_trades,
                    "final_capital": round(m.final_capital, 2),
                    "passed_validation": sr.passed_validation,
                    "cagr_pct": round(m.cagr_pct, 2),
                    "payoff_ratio": round(m.payoff_ratio, 2),
                })

    ranking_entries.sort(
        key=lambda e: (
            e["passed_validation"],
            e["sharpe_ratio"],
            -abs(e["max_drawdown_pct"]),
            e["profit_factor"],
        ),
        reverse=True,
    )
    return ConsolidatedRanking(entries=ranking_entries)


def compute_weighted_score(entry: dict, weights: Optional[dict[str, float]] = None) -> float:
    """Compute weighted ranking score from key performance fields."""
    if weights is None:
        weights = {"sharpe": 1.5, "drawdown": 2.0, "profit_factor": 1.0}

    sharpe = max(0, entry.get("sharpe_ratio", 0))
    dd_penalty = max(0, abs(entry.get("max_drawdown_pct", 0))) / 100
    pf = min(5, entry.get("profit_factor", 0))

    score = (
        sharpe * weights.get("sharpe", 1.5)
        - dd_penalty * weights.get("drawdown", 2.0)
        + pf * weights.get("profit_factor", 1.0)
    )
    return round(score, 4)
