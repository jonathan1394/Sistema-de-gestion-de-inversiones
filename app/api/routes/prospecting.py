"""Prospecting endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Query, Request

from app.data.binance_client import BinanceClient
from app.database.connection import get_connection
from app.prospecting.db import (
    Prospect,
    add_prospect,
    get_all_prospects,
    get_prospect,
    update_prospect_status,
)
from app.prospecting.ranking import generate_ranking
from app.prospecting.screener import ProspectScreener

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prospecting", tags=["prospecting"])


def _prospect_to_dict(p: Prospect) -> dict[str, Any]:
    return {
        "symbol": p.symbol,
        "interval": p.interval,
        "status": p.status,
        "added_at": p.added_at,
        "last_analysis_at": p.last_analysis_at,
        "score": p.score,
        "trend": p.trend,
        "volatility": p.volatility,
        "volume_profile": p.volume_profile,
        "rsi_condition": p.rsi_condition,
        "signals_count": p.signals_count,
        "metadata": p.metadata,
        "notes": p.notes,
    }


@router.get("/prospects")
def prospects(
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    status: str | None = Query(default=None),
    min_score: float | None = Query(default=None),
) -> dict[str, Any]:
    s = request.app.state.settings
    conn = get_connection(s.database.path)
    items = get_all_prospects(conn)
    if status:
        items = [p for p in items if p.status == status]
    if min_score is not None:
        items = [p for p in items if p.score >= float(min_score)]

    start = (page - 1) * limit
    page_items = items[start : start + limit]
    data = [_prospect_to_dict(p) for p in page_items]
    return {
        "status": "ok",
        "data": data,
        "error": None,
        "meta": {"page": page, "limit": limit, "returned": len(data), "total": len(items)},
    }


@router.post("/scan")
def scan(request: Request, payload: dict[str, Any] = Body(default={})):  # noqa: B006
    s = request.app.state.settings
    conn = get_connection(s.database.path)
    client = BinanceClient(s.binance)
    screener = ProspectScreener(
        client=client,
        connection=conn,
        download_if_missing=bool(s.prospecting.get("auto_download", True)),
        limit_candles=int(s.prospecting.get("max_candles_for_analysis", 200)),
        weights=dict(s.prospecting.get("scoring_weights", {}) or {}),
    )
    symbol = payload.get("symbol")
    interval = str(payload.get("interval") or s.prospecting.get("default_interval", "1d"))
    if symbol:
        screened = screener.run_on_symbol(str(symbol), interval=interval)
        single = screened.__dict__ if screened is not None else None
        return {"status": "ok", "data": single, "error": None, "meta": {}}

    result = screener.run_on_all()
    assets = [a.__dict__ for a in result.assets]
    return {"status": "ok", "data": assets, "error": None, "meta": {"count": len(assets)}}


@router.get("/ranking")
def ranking(request: Request) -> dict[str, Any]:
    s = request.app.state.settings
    conn = get_connection(s.database.path)
    items = get_all_prospects(conn)
    ranks = generate_ranking(items, settings=s, conn=conn)
    data = [r.__dict__ for r in ranks]
    return {"status": "ok", "data": data, "error": None, "meta": {"count": len(data)}}


@router.get("/decision/{symbol}")
def decision(request: Request, symbol: str, interval: str = Query(default="1d")) -> dict[str, Any]:
    """Return a lightweight decision view based on current prospect score."""
    s = request.app.state.settings
    conn = get_connection(s.database.path)
    p = get_prospect(conn, symbol, interval)
    if p is None:
        return {
            "status": "ok",
            "data": {"symbol": symbol.upper(), "interval": interval, "found": False},
            "error": None,
            "meta": {},
        }
    # Ranking already computes confluence/recommendation.
    r = generate_ranking([p], settings=s, conn=conn)[0]
    return {"status": "ok", "data": r.__dict__, "error": None, "meta": {}}


@router.post("/prospects/status")
def set_status(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    s = request.app.state.settings
    conn = get_connection(s.database.path)
    symbol = str(payload.get("symbol", "")).upper()
    interval = str(payload.get("interval", "1d"))
    new_status = str(payload.get("status", "watching"))
    update_prospect_status(conn, symbol, interval, new_status)
    return {"status": "ok", "data": {"symbol": symbol, "interval": interval, "status": new_status}, "error": None, "meta": {}}


@router.post("/prospects/add")
def add(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    s = request.app.state.settings
    conn = get_connection(s.database.path)
    symbol = str(payload.get("symbol", "")).upper()
    interval = str(payload.get("interval") or s.prospecting.get("default_interval", "1d"))
    notes = str(payload.get("notes", ""))
    p = add_prospect(conn, symbol, interval=interval, notes=notes)
    return {"status": "ok", "data": _prospect_to_dict(p), "error": None, "meta": {}}
