"""Market data endpoints."""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request

from app.ai.market_summary import generate_market_summary
from app.data.market_data import get_candles
from app.database.connection import get_connection
from app.prospecting.market_decision import compute_confluence

router = APIRouter(prefix="/market", tags=["market"])


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
        "data": {
            "symbol": last.symbol,
            "interval": last.interval,
            "price": last.close,
            "ts": last.close_time,
        },
        "error": None,
        "meta": {},
    }


@router.get("/summary")
def summary(
    request: Request,
    symbols: str = Query(default="BTCUSDT,ETHUSDT,SOLUSDT"),
    interval: str = Query(default="1h"),
) -> dict[str, Any]:
    settings = request.app.state.settings
    conn = get_connection(settings.database.path)
    out: list[dict[str, Any]] = []
    for sym in [s.strip() for s in symbols.split(",") if s.strip()]:
        rows = get_candles(conn, symbol=sym, interval=interval, limit=1, desc=True)
        if not rows:
            continue
        last = rows[-1]
        out.append(
            {
                "symbol": last.symbol,
                "interval": last.interval,
                "price": last.close,
                "ts": last.close_time,
            }
        )
    return {"status": "ok", "data": out, "error": None, "meta": {"count": len(out)}}


@router.get("/analysis/{symbol}")
def market_analysis(
    request: Request,
    symbol: str,
    intervals: str = Query(default="1h,4h,1d"),
) -> dict[str, Any]:
    """Multi-timeframe market analysis with confluence score."""
    s = request.app.state.settings
    conn = get_connection(s.database.path)
    tf_list = [i.strip() for i in intervals.split(",") if i.strip()]

    tf_results = []
    for interval in tf_list:
        candles = get_candles(conn, symbol=symbol, interval=interval, limit=200, desc=True)
        if not candles or len(candles) < 50:
            continue
        df = _candles_to_dataframe(candles)
        try:
            summary = generate_market_summary(df, symbol=symbol, period=interval)
        except (ValueError, KeyError):
            continue
        tf_results.append({
            "interval": interval,
            "price": summary.close_price,
            "return_pct": summary.return_pct,
            "trend": summary.condition.trend,
            "volatility": summary.condition.volatility,
            "rsi": summary.condition.rsi_condition,
            "volume": summary.condition.volume_profile,
            "summary_text": summary.condition.summary,
            "key_levels": summary.key_levels,
            "volatility_pct": summary.volatility_pct,
        })

    confluence = compute_confluence(tf_results)
    return {
        "status": "ok",
        "data": {
            "symbol": symbol.upper(),
            "timeframes": tf_results,
            "confluence": confluence,
            "total_timeframes": len(tf_results),
        },
        "error": None,
        "meta": {},
    }
