"""Market data endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.data.market_data import get_candles
from app.database.connection import get_connection


router = APIRouter(prefix="/market", tags=["market"])


@router.get("/candles/{symbol}/{interval}")
def candles(
    request: Request,
    symbol: str,
    interval: str,
    start_ms: int | None = Query(default=None),
    end_ms: int | None = Query(default=None),
    limit: int | None = Query(default=500, ge=1, le=5000),
    desc: bool = Query(default=False),
) -> dict[str, Any]:
    settings = request.app.state.settings
    conn = get_connection(settings.database.path)
    rows = get_candles(
        connection=conn,
        symbol=symbol,
        interval=interval,
        start_time_ms=start_ms,
        end_time_ms=end_ms,
        limit=limit,
        desc=desc,
    )
    data = [
        {
            "symbol": c.symbol,
            "interval": c.interval,
            "open_time": c.open_time,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
            "close_time": c.close_time,
            "quote_asset_volume": c.quote_asset_volume,
            "number_of_trades": c.number_of_trades,
            "taker_buy_base_asset_volume": c.taker_buy_base_asset_volume,
            "taker_buy_quote_asset_volume": c.taker_buy_quote_asset_volume,
        }
        for c in rows
    ]
    return {"status": "ok", "data": data, "error": None, "meta": {"count": len(data)}}


@router.get("/price/{symbol}")
def price(request: Request, symbol: str, interval: str = Query(default="1h")) -> dict[str, Any]:
    settings = request.app.state.settings
    conn = get_connection(settings.database.path)
    rows = get_candles(conn, symbol=symbol, interval=interval, limit=1, desc=True)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No candle data for {symbol} {interval}")
    last = rows[-1]
    return {
        "status": "ok",
        "data": {"symbol": last.symbol, "interval": last.interval, "price": last.close, "ts": last.close_time},
        "error": None,
        "meta": {},
    }


@router.get("/summary")
def summary(request: Request, symbols: str = Query(default="BTCUSDT,ETHUSDT,SOLUSDT"), interval: str = Query(default="1h")) -> dict[str, Any]:
    settings = request.app.state.settings
    conn = get_connection(settings.database.path)
    out: list[dict[str, Any]] = []
    for sym in [s.strip() for s in symbols.split(",") if s.strip()]:
        rows = get_candles(conn, symbol=sym, interval=interval, limit=1, desc=True)
        if not rows:
            continue
        last = rows[-1]
        out.append({"symbol": last.symbol, "interval": last.interval, "price": last.close, "ts": last.close_time})
    return {"status": "ok", "data": out, "error": None, "meta": {"count": len(out)}}
