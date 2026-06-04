"""Performance and trade-statistics computation for backtests."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.backtesting.engine import BacktestResult


@dataclass
class BacktestMetrics:
    roi_pct: float = 0.0
    cagr_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    payoff_ratio: float = 0.0
    avg_hold_bars: float = 0.0
    total_fees: float = 0.0
    final_capital: float = 0.0
    initial_capital: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    largest_win_pct: float = 0.0
    largest_loss_pct: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    time_in_market_pct: float = 0.0


_BARS_PER_DAY: dict[str, float] = {
    "1m": 1440,
    "5m": 288,
    "15m": 96,
    "30m": 48,
    "1h": 24,
    "2h": 12,
    "4h": 6,
    "6h": 4,
    "8h": 3,
    "12h": 2,
    "1d": 1,
}


def _bars_per_day(interval: str) -> float:
    return _BARS_PER_DAY.get(interval, 1)


def _annualization_factor(interval: str) -> float:
    return np.sqrt(365.25 * 24 * 60 / _bars_per_day(interval))


def _compute_performance_metrics(
    metrics: BacktestMetrics,
    equity: pd.Series,
    interval: str,
    initial: float,
    final: float,
) -> None:
    days = (equity.index[-1] - equity.index[0]).total_seconds() / 86400.0
    years = days / 365.25
    if years > 0.01 and initial > 0 and final > 0:
        metrics.cagr_pct = ((final / initial) ** (1 / years) - 1) * 100

    cumulative = equity / initial
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    metrics.max_drawdown_pct = float(drawdown.min() * 100)

    returns = equity.pct_change().dropna()
    if len(returns) < 2:
        return

    ann = _annualization_factor(interval)
    std = returns.std()
    if std > 0:
        metrics.sharpe_ratio = float(ann * returns.mean() / std)

    neg_returns = returns[returns < 0]
    neg_std = neg_returns.std()
    if neg_std > 0:
        metrics.sortino_ratio = float(ann * returns.mean() / neg_std)


def _compute_trade_metrics(
    metrics: BacktestMetrics,
    trades: list,
    pnl_pcts: np.ndarray,
    wins: np.ndarray,
    losses: np.ndarray,
    equity: pd.Series,
) -> None:
    metrics.gross_profit = float(np.sum([t.pnl for t in trades if t.pnl > 0]))
    metrics.gross_loss = float(abs(np.sum([t.pnl for t in trades if t.pnl < 0])))

    if metrics.gross_loss > 0:
        metrics.profit_factor = metrics.gross_profit / metrics.gross_loss
    elif metrics.gross_profit > 0:
        metrics.profit_factor = float("inf")

    if metrics.total_trades > 0:
        metrics.expectancy = float(np.mean(pnl_pcts)) * 100

    if len(wins) > 0:
        metrics.avg_win_pct = float(np.mean(wins)) * 100
        metrics.largest_win_pct = float(np.max(wins)) * 100
    if len(losses) > 0:
        metrics.avg_loss_pct = float(np.mean(losses)) * 100
        metrics.largest_loss_pct = float(np.min(losses)) * 100

    if metrics.avg_loss_pct != 0:
        metrics.payoff_ratio = abs(metrics.avg_win_pct / metrics.avg_loss_pct)
    elif metrics.avg_win_pct > 0:
        metrics.payoff_ratio = float("inf")

    hold_bars = [t.hold_bars for t in trades]
    metrics.avg_hold_bars = float(np.mean(hold_bars)) if hold_bars else 0.0

    max_wins = 0
    max_losses = 0
    streak = 0
    positive = True
    for pnl in pnl_pcts:
        if pnl > 0:
            if not positive:
                streak = 0
                positive = True
            streak += 1
            max_wins = max(max_wins, streak)
        elif pnl < 0:
            if positive:
                streak = 0
                positive = False
            streak += 1
            max_losses = max(max_losses, streak)
    metrics.consecutive_wins = max_wins
    metrics.consecutive_losses = max_losses

    total_bars = len(equity)
    open_bars = sum(t.hold_bars for t in trades)
    if total_bars > 0:
        metrics.time_in_market_pct = (open_bars / total_bars) * 100


def compute_metrics(result: BacktestResult) -> BacktestMetrics:
    """Compute aggregate metrics from one backtest result."""
    metrics = BacktestMetrics(
        initial_capital=result.initial_capital,
        final_capital=result.final_capital,
        total_fees=result.total_fees,
    )

    equity = result.equity_curve
    trades = result.trades

    if len(equity) < 2:
        return metrics

    initial = result.initial_capital
    final = result.final_capital
    metrics.roi_pct = ((final - initial) / initial) * 100

    _compute_performance_metrics(metrics, equity, result.interval, initial, final)

    if not trades:
        return metrics

    metrics.total_trades = len(trades)
    pnl_pcts = np.array([t.pnl_pct for t in trades])
    wins = pnl_pcts[pnl_pcts > 0]
    losses = pnl_pcts[pnl_pcts < 0]

    metrics.winning_trades = len(wins)
    metrics.losing_trades = len(losses)

    if metrics.total_trades > 0:
        metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100

    _compute_trade_metrics(metrics, trades, pnl_pcts, wins, losses, equity)

    return metrics
