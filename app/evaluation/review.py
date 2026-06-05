"""Helpers to build an investment evaluation summary."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.backtesting.comparator import compare_strategies
from app.data.data_validator import INTERVAL_MS, validate_candle_sequence
from app.data.market_data import get_candles
from app.governance.decision_engine import evaluate_investment_decision
from app.prospecting.db import get_prospect
from app.prospecting.ranking import generate_ranking


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _candles_to_dataframe(candles: list) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime([c.open_time for c in candles], unit="ms", utc=True),
            "open": [c.open for c in candles],
            "high": [c.high for c in candles],
            "low": [c.low for c in candles],
            "close": [c.close for c in candles],
            "volume": [c.volume for c in candles],
        }
    )


def summarize_data_health(
    connection,
    *,
    symbols: list[str],
    intervals: list[str],
    lookback: int = 200,
) -> list[dict[str, Any]]:
    """Return freshness and continuity checks for a symbol/timeframe set."""
    out: list[dict[str, Any]] = []
    now_ms = _now_ms()

    for symbol in symbols:
        for interval in intervals:
            candles = get_candles(connection, symbol=symbol, interval=interval, limit=lookback, desc=True)
            if not candles:
                out.append(
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "count": 0,
                        "fresh": False,
                        "enough_history": False,
                        "continuity_ok": False,
                        "status": "missing",
                        "validation_errors": ["No candles returned"],
                        "latest_open_time": None,
                        "latest_close_time": None,
                        "latest_price": None,
                        "age_minutes": None,
                    }
                )
                continue

            errors = validate_candle_sequence([c.open_time for c in candles], interval)
            latest = candles[-1]
            age_minutes = round((now_ms - int(latest.close_time)) / 60_000, 2)
            max_age_ms = INTERVAL_MS.get(interval, 0) * 3
            fresh = max_age_ms > 0 and (now_ms - int(latest.close_time)) <= max_age_ms
            enough_history = len(candles) >= 50
            continuity_ok = not errors

            status = "ok"
            if not fresh:
                status = "stale"
            if not enough_history:
                status = "short_history"
            if not continuity_ok:
                status = "gaps_detected"

            out.append(
                {
                    "symbol": symbol,
                    "interval": interval,
                    "count": len(candles),
                    "fresh": fresh,
                    "enough_history": enough_history,
                    "continuity_ok": continuity_ok,
                    "status": status,
                    "validation_errors": errors,
                    "latest_open_time": latest.open_time,
                    "latest_close_time": latest.close_time,
                    "latest_price": latest.close,
                    "age_minutes": age_minutes,
                }
            )

    return out


def build_investment_review(
    settings,
    connection,
    *,
    symbol: str,
    interval: str,
    backtest_interval: str,
    backtest_limit: int,
    suggested_amount_usdt: float,
) -> dict[str, Any]:
    """Build a unified review used by API, UI and CLI."""
    symbol = symbol.upper()
    timeframes = list(settings.timeframes)
    data_health = summarize_data_health(
        connection,
        symbols=[symbol],
        intervals=sorted(set(timeframes + [interval, backtest_interval])),
    )

    prospect = get_prospect(connection, symbol, interval)
    ranking = None
    if prospect is not None:
        ranking = generate_ranking([prospect], settings=settings, conn=connection)[0]

    risk = None
    if prospect is not None:
        risk = evaluate_investment_decision(
            symbol=symbol,
            interval=interval,
            score=prospect.score,
            suggested_amount_usdt=suggested_amount_usdt,
        )

    backtest_summary: dict[str, Any] = {
        "interval": backtest_interval,
        "limit": backtest_limit,
        "ready": False,
        "reason": "No candles available",
        "best_strategy": None,
        "strategies": [],
    }
    backtest_candles = get_candles(
        connection,
        symbol=symbol,
        interval=backtest_interval,
        limit=backtest_limit,
    )
    if len(backtest_candles) >= 50:
        comparison = compare_strategies(
            data=_candles_to_dataframe(backtest_candles),
            symbol=symbol,
            interval=backtest_interval,
            initial_capital=settings.capital.initial_usdt,
            commission_pct=settings.backtesting.default_commission_pct,
            slippage_pct=settings.backtesting.default_slippage_pct,
        )
        strategies = []
        for result in comparison.strategy_results:
            metrics = result.metrics
            strategies.append(
                {
                    "strategy_name": result.strategy_name,
                    "passed_validation": result.passed_validation,
                    "metrics": {
                        "total_trades": metrics.total_trades,
                        "profit_factor": round(metrics.profit_factor, 2),
                        "sharpe_ratio": round(metrics.sharpe_ratio, 2),
                        "max_drawdown_pct": round(metrics.max_drawdown_pct, 2),
                        "roi_pct": round(metrics.roi_pct, 2),
                    },
                }
            )
        backtest_summary = {
            "interval": backtest_interval,
            "limit": backtest_limit,
            "ready": True,
            "reason": None,
            "best_strategy": comparison.best.strategy_name if comparison.best else None,
            "strategies": strategies,
        }
    elif backtest_candles:
        backtest_summary = {
            **backtest_summary,
            "reason": f"Insufficient candles for backtest: {len(backtest_candles)}",
        }

    all_data_ready = all(
        row["fresh"] and row["enough_history"] and row["continuity_ok"] for row in data_health
    )
    best_strategy = next(
        (row for row in backtest_summary["strategies"] if row["strategy_name"] == backtest_summary["best_strategy"]),
        None,
    )
    min_confluence_for_invest = settings.prospecting["recommendation"].get(
        "min_confluence_for_invertir", 2
    )
    investing_score = settings.prospecting["recommendation"].get("invertir_threshold", 0.75)

    protocol_checks = {
        "in_universe": symbol in settings.symbols,
        "configured_interval": interval in timeframes,
        "data_ready": all_data_ready,
        "prospect_available": prospect is not None,
        "score_ready": prospect is not None and prospect.score >= investing_score,
        "confluence_ready": ranking is not None and ranking.confluence >= min_confluence_for_invest,
        "backtest_ready": best_strategy is not None and best_strategy["passed_validation"],
        "risk_ready": risk is not None and risk.approved,
    }
    investable = all(protocol_checks.values())

    return {
        "symbol": symbol,
        "interval": interval,
        "backtest_interval": backtest_interval,
        "suggested_amount_usdt": suggested_amount_usdt,
        "universe": {
            "symbols": list(settings.symbols),
            "timeframes": timeframes,
            "symbol_configured": symbol in settings.symbols,
        },
        "data_health": data_health,
        "prospect": None
        if prospect is None
        else {
            "symbol": prospect.symbol,
            "interval": prospect.interval,
            "status": prospect.status,
            "score": prospect.score,
            "trend": prospect.trend,
            "signals_count": prospect.signals_count,
            "last_analysis_at": prospect.last_analysis_at,
            "notes": prospect.notes,
        },
        "ranking": None if ranking is None else asdict(ranking),
        "backtest": backtest_summary,
        "risk": None
        if risk is None
        else {
            "approved": risk.approved,
            "recommendation": risk.recommendation,
            "action": risk.action,
            "reason": risk.reason,
            "blocking_rule": risk.blocking_rule,
            "score": risk.score,
            "confluence": risk.confluence,
            "current_price": risk.current_price,
            "quantity": risk.quantity,
        },
        "protocol": {
            "checks": protocol_checks,
            "min_trades": settings.backtesting.min_trades_for_validation,
            "min_profit_factor": settings.backtesting.min_profit_factor,
            "min_sharpe_ratio": settings.backtesting.min_sharpe_ratio,
            "investing_score_threshold": investing_score,
            "min_confluence_for_invest": min_confluence_for_invest,
            "status": "investable" if investable else "review_required",
        },
    }
