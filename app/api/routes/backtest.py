"""Backtesting endpoints."""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, Body, HTTPException, Request

from app.backtesting import BacktestEngine, compute_metrics
from app.backtesting.comparator import compare_strategies
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.strategies import (
    DCADynamic,
    MovingAverageCrossover,
    RebalanceStrategy,
    RSIStrategy,
    TrendFollowing,
)

router = APIRouter(prefix="/backtest", tags=["backtest"])


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


def _make_strategy(name: str, symbol: str, params: dict[str, Any]) -> Any:
    name_norm = name.strip().lower()
    if name_norm in {"ma", "ma_crossover", "moving_average_crossover"}:
        return MovingAverageCrossover(parameters={"symbol": symbol, **params})
    if name_norm in {"rsi", "rsi_strategy"}:
        return RSIStrategy(parameters={"symbol": symbol, **params})
    if name_norm in {"trend", "trend_following"}:
        return TrendFollowing(parameters={"symbol": symbol, **params})
    if name_norm in {"dca", "dca_dynamic"}:
        return DCADynamic(parameters={"symbol": symbol, **params})
    if name_norm in {"rebalance", "rebalance_strategy"}:
        return RebalanceStrategy(parameters={"symbol": symbol, **params})
    raise ValueError(f"Unknown strategy: {name}")


@router.get("/strategies")
def strategies() -> dict[str, Any]:
    return {
        "status": "ok",
        "data": [
            {"id": "ma", "label": "MA Crossover"},
            {"id": "rsi", "label": "RSI"},
            {"id": "trend", "label": "Trend Following"},
            {"id": "dca", "label": "DCA Dinamico"},
            {"id": "rebalance", "label": "Rebalanceo"},
        ],
        "error": None,
        "meta": {},
    }


@router.post("/run")
def run_backtest(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    s = request.app.state.settings
    symbol = str(payload.get("symbol", "BTCUSDT")).upper()
    interval = str(payload.get("interval", "1h"))
    strategy_name = str(payload.get("strategy", "ma"))
    params = dict(payload.get("params", {}) or {})
    capital = float(payload.get("capital", s.capital.initial_usdt))
    limit = int(payload.get("limit", 1000))

    conn = get_connection(s.database.path)
    candles = get_candles(connection=conn, symbol=symbol, interval=interval, limit=limit)
    if len(candles) < 50:
        raise HTTPException(status_code=400, detail=f"Insufficient candles: {len(candles)}")

    data = _candles_to_dataframe(candles)
    try:
        strategy = _make_strategy(strategy_name, symbol=symbol, params=params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    engine = BacktestEngine(
        strategy=strategy,
        data=data,
        initial_capital=capital,
        commission_pct=s.backtesting.default_commission_pct,
        slippage_pct=s.backtesting.default_slippage_pct,
        symbol=symbol,
        interval=interval,
    )
    result = engine.run()
    metrics = compute_metrics(result)

    trades = [
        {
            "entry_time": str(t.entry_time),
            "exit_time": str(t.exit_time),
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "quantity": t.quantity,
            "fees": t.fees,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "hold_bars": t.hold_bars,
            "reason_entry": t.reason_entry,
            "reason_exit": t.reason_exit,
        }
        for t in result.trades
    ]
    equity = [
        {"timestamp": str(ts), "equity": float(val)} for ts, val in result.equity_curve.items()
    ]

    return {
        "status": "ok",
        "data": {
            "result": {
                "symbol": result.symbol,
                "interval": result.interval,
                "initial_capital": result.initial_capital,
                "final_capital": result.final_capital,
                "total_fees": result.total_fees,
                "strategy_name": result.strategy_name,
                "parameters": result.parameters,
            },
            "metrics": metrics.__dict__,
            "trades": trades,
            "equity_curve": equity,
        },
        "error": None,
        "meta": {},
    }


@router.post("/compare")
def compare_backtests(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Run all strategies on the same data and return comparative results."""
    s = request.app.state.settings
    symbol = str(payload.get("symbol", "BTCUSDT")).upper()
    interval = str(payload.get("interval", "4h"))
    capital = float(payload.get("capital", s.capital.initial_usdt))
    limit = int(payload.get("limit", 500))

    conn = get_connection(s.database.path)
    candles = get_candles(connection=conn, symbol=symbol, interval=interval, limit=limit)
    if len(candles) < 50:
        raise HTTPException(status_code=400, detail=f"Insufficient candles: {len(candles)}")

    data = _candles_to_dataframe(candles)
    result = compare_strategies(
        data=data, symbol=symbol, interval=interval, initial_capital=capital,
        commission_pct=s.backtesting.default_commission_pct,
        slippage_pct=s.backtesting.default_slippage_pct,
    )

    strategies_data = []
    for sr in result.strategy_results:
        m = sr.metrics
        strategies_data.append({
            "strategy_name": sr.strategy_name,
            "parameters": sr.parameters,
            "passed_validation": sr.passed_validation,
            "metrics": {
                "total_trades": m.total_trades,
                "win_rate": round(m.win_rate, 1),
                "profit_factor": round(m.profit_factor, 2),
                "sharpe_ratio": round(m.sharpe_ratio, 2),
                "sortino_ratio": round(m.sortino_ratio, 2),
                "max_drawdown_pct": round(m.max_drawdown_pct, 2),
                "roi_pct": round(m.roi_pct, 2),
                "final_capital": round(m.final_capital, 2),
                "cagr_pct": round(m.cagr_pct, 2),
                "payoff_ratio": round(m.payoff_ratio, 2),
            },
        })

    return {
        "status": "ok",
        "data": {
            "symbol": symbol,
            "interval": interval,
            "initial_capital": capital,
            "best_strategy": result.best.strategy_name if result.best else None,
            "strategies": strategies_data,
        },
        "error": None,
        "meta": {},
    }
