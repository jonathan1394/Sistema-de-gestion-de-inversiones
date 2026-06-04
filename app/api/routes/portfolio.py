"""Paper portfolio endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request

from app.database.connection import get_connection
from app.governance.decision_engine import evaluate_investment_decision
from app.paper_trading.storage import (
    get_all_positions,
    get_snapshots,
    get_trades,
    init_portfolio_tables,
    record_trade,
    remove_position,
    upsert_position,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/state")
def state(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    conn = get_connection(settings.database.path)
    init_portfolio_tables(conn)
    positions = get_all_positions(conn)
    positions_data = [
        {
            "symbol": p.symbol,
            "quantity": p.quantity,
            "entry_price": p.entry_price,
            "current_price": p.current_price,
            "unrealized_pnl": p.unrealized_pnl,
            "entry_time": p.entry_time,
            "updated_at": p.updated_at,
        }
        for p in positions
    ]
    return {"status": "ok", "data": {"positions": positions_data}, "error": None, "meta": {}}


@router.get("/trades")
def trades(
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=500),
    symbol: str | None = Query(default=None),
) -> dict[str, Any]:
    settings = request.app.state.settings
    conn = get_connection(settings.database.path)
    init_portfolio_tables(conn)
    # Storage currently supports only a "recent limit". Use page by over-fetch.
    fetch = page * limit
    items = get_trades(conn, symbol=symbol, limit=fetch)
    start = (page - 1) * limit
    page_items = items[start : start + limit]
    data = [
        {
            "id": t.id,
            "symbol": t.symbol,
            "interval": t.interval,
            "action": t.action,
            "quantity": t.quantity,
            "price": t.price,
            "commission": t.commission,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "reason": t.reason,
            "created_at": t.created_at,
        }
        for t in page_items
    ]
    return {
        "status": "ok",
        "data": data,
        "error": None,
        "meta": {"page": page, "limit": limit, "returned": len(data)},
    }


@router.post("/trade")
def execute_trade(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Execute a paper trade (buy/sell/close) and record it."""
    s = request.app.state.settings
    conn = get_connection(s.database.path)
    init_portfolio_tables(conn)

    symbol = str(payload.get("symbol", "")).upper()
    action = str(payload.get("action", "buy")).lower()
    amount_usdt = float(payload.get("amount_usdt", 50))
    interval = str(payload.get("interval", "4h"))

    if not symbol:
        raise HTTPException(status_code=400, detail="symbol is required")

    price_resp = _get_current_price(conn, symbol)
    if price_resp is None:
        raise HTTPException(status_code=400, detail=f"No price data for {symbol}")
    current_price = float(price_resp)

    if action == "buy":
        quantity = amount_usdt / current_price
        trade = record_trade(
            connection=conn, symbol=symbol, action="BUY", quantity=quantity,
            price=current_price,
            commission=current_price * quantity * s.backtesting.default_commission_pct,
            reason=payload.get("reason", "Manual paper buy"),
            interval=interval,
        )
        upsert_position(
            connection=conn, symbol=symbol, quantity=quantity,
            entry_price=current_price, current_price=current_price,
        )
        return {
            "status": "ok",
            "data": {
                "action": "BUY",
                "symbol": symbol,
                "quantity": round(quantity, 6),
                "price": current_price,
                "trade_id": trade.id,
            },
            "error": None,
            "meta": {},
        }

    if action == "sell":
        positions = get_all_positions(conn)
        pos = next((p for p in positions if p.symbol == symbol), None)
        if not pos:
            raise HTTPException(status_code=400, detail=f"No position open for {symbol}")
        quantity = pos.quantity
        pnl = quantity * (current_price - pos.entry_price)
        pnl_pct = ((current_price - pos.entry_price) / pos.entry_price) * 100
        trade = record_trade(
            connection=conn, symbol=symbol, action="SELL", quantity=quantity,
            price=current_price,
            commission=current_price * quantity * s.backtesting.default_commission_pct,
            pnl=pnl, pnl_pct=pnl_pct,
            reason=payload.get("reason", "Manual paper sell"),
            interval=interval,
        )
        remove_position(conn, symbol)
        return {
            "status": "ok",
            "data": {
                "action": "SELL",
                "symbol": symbol,
                "quantity": round(quantity, 6),
                "price": current_price,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "trade_id": trade.id,
            },
            "error": None,
            "meta": {},
        }

    if action == "evaluate":
        score = float(payload.get("score", 0.5))
        decision = evaluate_investment_decision(
            symbol=symbol, interval=interval, score=score,
            suggested_amount_usdt=amount_usdt,
        )
        return {
            "status": "ok",
            "data": {
                "symbol": symbol,
                "approved": decision.approved,
                "recommendation": decision.recommendation,
                "reason": decision.reason,
                "blocking_rule": decision.blocking_rule,
                "suggested_amount_usdt": decision.suggested_amount_usdt,
                "score": decision.score,
                "confluence": decision.confluence,
                "current_price": decision.current_price,
                "quantity": decision.quantity,
            },
            "error": None,
            "meta": {},
        }

    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


def _get_current_price(conn, symbol: str) -> float | None:
    from app.data.market_data import get_candles
    for interval in ("1h", "4h", "1d"):
        candles = get_candles(conn, symbol=symbol, interval=interval, limit=1, desc=True)
        if candles:
            return float(candles[0].close)
    return None


@router.get("/snapshots")
def snapshots(
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    settings = request.app.state.settings
    conn = get_connection(settings.database.path)
    init_portfolio_tables(conn)
    fetch = page * limit
    items = get_snapshots(conn, limit=fetch)
    start = (page - 1) * limit
    data = items[start : start + limit]
    return {
        "status": "ok",
        "data": data,
        "error": None,
        "meta": {"page": page, "limit": limit, "returned": len(data)},
    }
