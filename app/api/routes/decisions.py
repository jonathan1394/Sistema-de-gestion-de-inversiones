"""Decision log endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request

from app.governance.decision_log import get_recent_decisions, log_decision

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("")
def list_decisions(
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=500),
    symbol: str | None = Query(default=None),
    approved_only: bool = Query(default=False),
    rejected_only: bool = Query(default=False),
) -> dict[str, Any]:
    s = request.app.state.settings
    fetch = page * limit
    items = get_recent_decisions(
        limit=fetch,
        symbol=symbol.upper() if symbol else None,
        approved_only=approved_only,
        rejected_only=rejected_only,
        settings=s,
    )
    start = (page - 1) * limit
    page_items = items[start : start + limit]
    data = [d.__dict__ for d in page_items]
    return {
        "status": "ok",
        "data": data,
        "error": None,
        "meta": {"page": page, "limit": limit, "returned": len(data)},
    }


@router.post("")
def create_decision(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Manually log a decision entry."""
    s = request.app.state.settings
    decision_type = str(payload.get("decision_type", "MANUAL"))
    symbol = payload.get("symbol")
    strategy_name = payload.get("strategy_name")
    timeframe = payload.get("timeframe")
    approved = bool(payload.get("approved", True))
    reason = str(payload.get("reason", ""))
    input_data = payload.get("input_data", {})
    output_data = payload.get("output_data", {})

    try:
        decision_id = log_decision(
            decision_type=decision_type,
            symbol=str(symbol).upper() if symbol else None,
            strategy_name=str(strategy_name) if strategy_name else None,
            timeframe=str(timeframe) if timeframe else None,
            mode=s.trading.mode,
            approved=approved,
            reason=reason,
            input_data=input_data,
            output_data=output_data,
            settings=s,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "status": "ok",
        "data": {"decision_id": decision_id},
        "error": None,
        "meta": {},
    }
