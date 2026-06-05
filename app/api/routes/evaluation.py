"""Investment evaluation endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from app.database.connection import get_connection
from app.evaluation.review import build_investment_review, summarize_data_health

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/data-health")
def data_health(
    request: Request,
    symbols: str | None = Query(default=None),
    intervals: str | None = Query(default=None),
) -> dict[str, Any]:
    settings = request.app.state.settings
    conn = get_connection(settings.database.path)
    symbol_list = [s.strip().upper() for s in (symbols or ",".join(settings.symbols)).split(",") if s.strip()]
    interval_list = [i.strip() for i in (intervals or ",".join(settings.timeframes)).split(",") if i.strip()]
    data = summarize_data_health(conn, symbols=symbol_list, intervals=interval_list)
    return {"status": "ok", "data": data, "error": None, "meta": {"count": len(data)}}


@router.get("/investment/{symbol}")
def investment_review(
    request: Request,
    symbol: str,
    interval: str = Query(default="1d"),
    backtest_interval: str = Query(default="4h"),
    backtest_limit: int = Query(default=500, ge=50, le=5000),
    amount: float = Query(default=50.0, gt=0),
) -> dict[str, Any]:
    settings = request.app.state.settings
    conn = get_connection(settings.database.path)
    data = build_investment_review(
        settings,
        conn,
        symbol=symbol,
        interval=interval,
        backtest_interval=backtest_interval,
        backtest_limit=backtest_limit,
        suggested_amount_usdt=amount,
    )
    return {"status": "ok", "data": data, "error": None, "meta": {}}
