"""Paper portfolio endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, Request

from app.database.connection import get_connection
from app.paper_trading.storage import (
    get_all_positions,
    get_snapshots,
    get_trades,
    init_portfolio_tables,
)

logger = logging.getLogger(__name__)

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
