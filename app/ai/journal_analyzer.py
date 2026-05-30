from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TradeAnalysis:
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_hold_time: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0


@dataclass
class BehaviorFlags:
    revenge_trading: bool = False
    increasing_size_after_loss: bool = False
    closing_early: bool = False
    fomo_entries: bool = False
    ignoring_stops: bool = False
    details: list[str] = field(default_factory=list)


@dataclass
class StrategyInsight:
    best_timeframe: str = ""
    best_condition: str = ""
    weakness: str = ""
    suggestion: str = ""


@dataclass
class JournalReport:
    trade_analysis: TradeAnalysis
    behavior: BehaviorFlags
    insight: StrategyInsight
    summary: str


def analyze_trades(trades: list[dict]) -> TradeAnalysis:
    if not trades:
        return TradeAnalysis()

    pnls = [t.get("pnl_pct", 0) for t in trades if t.get("pnl_pct") is not None]
    if not pnls:
        return TradeAnalysis()

    analysis = TradeAnalysis(total_trades=len(pnls))
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    if analysis.total_trades > 0:
        analysis.win_rate = len(wins) / analysis.total_trades * 100
    if wins:
        analysis.avg_win = sum(wins) / len(wins)
        analysis.largest_win = max(wins)
    if losses:
        analysis.avg_loss = sum(losses) / len(losses)
        analysis.largest_loss = min(losses)
    if losses and sum(losses) != 0:
        gross_profit = sum(wins) if wins else 0
        gross_loss = abs(sum(losses)) if losses else 0
        analysis.profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    hold_times = [t.get("hold_bars", 0) for t in trades if t.get("hold_bars") is not None]
    if hold_times:
        analysis.avg_hold_time = sum(hold_times) / len(hold_times)

    streak = 0
    max_wins = 0
    max_losses = 0
    positive = True
    for p in pnls:
        if p > 0:
            if not positive:
                streak = 0
                positive = True
            streak += 1
            max_wins = max(max_wins, streak)
        elif p < 0:
            if positive:
                streak = 0
                positive = False
            streak += 1
            max_losses = max(max_losses, streak)
    analysis.consecutive_wins = max_wins
    analysis.consecutive_losses = max_losses

    return analysis


def analyze_behavior(trades: list[dict]) -> BehaviorFlags:
    flags = BehaviorFlags()
    if not trades or len(trades) < 3:
        return flags

    pnls = [t.get("pnl_pct", 0) for t in trades]
    sizes = [abs(t.get("quantity", 0)) for t in trades]

    for i in range(1, len(pnls)):
        if pnls[i - 1] < -2.0 and pnls[i] > 0:
            flags.revenge_trading = True
            flags.details.append(f"Trade {i}: Loss of {pnls[i-1]:.1f}% followed by immediate trade")

    for i in range(2, len(pnls)):
        if pnls[i - 1] < 0 and pnls[i - 2] < 0 and sizes[i] > sizes[i - 1] * 1.5 if i < len(sizes) else False:
            pass

    losing_streak = 0
    for i, p in enumerate(pnls):
        if p < 0:
            losing_streak += 1
            if losing_streak >= 3 and i + 1 < len(sizes) and sizes[i + 1] > sizes[i] * 1.2:
                flags.increasing_size_after_loss = True
                flags.details.append(f"Increasing position size after {losing_streak} consecutive losses")
        else:
            losing_streak = 0

    hold_times = [t.get("hold_bars", 0) for t in trades if t.get("hold_bars") is not None]
    if hold_times and len(hold_times) > 5:
        avg_hold = sum(hold_times) / len(hold_times)
        very_short = sum(1 for h in hold_times if h < avg_hold * 0.2)
        if very_short > len(hold_times) * 0.3:
            flags.closing_early = True
            flags.details.append(f"{very_short}/{len(hold_times)} trades held <20% of average hold time")

    return flags


def generate_insight(analysis: TradeAnalysis, behavior: BehaviorFlags) -> StrategyInsight:
    insight = StrategyInsight()

    if analysis.win_rate < 40:
        insight.weakness = "Low win rate — consider tightening entry criteria"
        insight.suggestion = "Add filtering conditions (trend, volume) before entry"
    elif analysis.win_rate > 70:
        insight.weakness = "High win rate but check if payoff ratio compensates for losses"
        insight.suggestion = "Consider letting winners run longer to improve risk/reward"

    if analysis.profit_factor < 1.0:
        insight.weakness = "Strategy is not profitable overall (profit factor < 1.0)"
        insight.suggestion = "Review stop-loss placement and take-profit targets"
    elif analysis.profit_factor < 1.5:
        insight.weakness = "Profit factor below recommended 1.5 minimum"
        insight.suggestion = "Test with different parameters or market conditions"

    if analysis.avg_loss and analysis.avg_win:
        if abs(analysis.avg_loss) > abs(analysis.avg_win):
            insight.weakness = "Average loss exceeds average win — poor risk/reward"
            insight.suggestion = "Tighten stop-losses or let winners run longer"

    if behavior.revenge_trading:
        insight.weakness = "Pattern of revenge trading detected after losses"
        insight.suggestion = "Implement a mandatory cooldown after losing trades"

    if behavior.increasing_size_after_loss:
        if "increasing" not in insight.weakness:
            insight.weakness = "Increasing position size after losses (martingale behavior)"
            insight.suggestion = "Enforce fixed position sizing regardless of recent outcomes"

    if not insight.weakness:
        insight.weakness = "No significant weaknesses detected in available data"
        insight.suggestion = "Continue monitoring and consider forward testing"

    return insight


def generate_journal_report(trades: list[dict]) -> JournalReport:
    if not trades:
        return JournalReport(
            trade_analysis=TradeAnalysis(),
            behavior=BehaviorFlags(),
            insight=StrategyInsight(),
            summary="No trades available for analysis.",
        )

    analysis = analyze_trades(trades)
    behavior = analyze_behavior(trades)
    insight = generate_insight(analysis, behavior)

    summary_parts = []
    summary_parts.append(
        f"Analyzed {analysis.total_trades} trades. "
        f"Win rate: {analysis.win_rate:.1f}%. "
        f"Profit factor: {analysis.profit_factor:.2f}."
    )

    if behavior.details:
        summary_parts.append(f"Behavior flags: {'; '.join(behavior.details)}")

    if insight.suggestion:
        summary_parts.append(f"Suggestion: {insight.suggestion}")

    return JournalReport(
        trade_analysis=analysis,
        behavior=behavior,
        insight=insight,
        summary=" ".join(summary_parts),
    )
