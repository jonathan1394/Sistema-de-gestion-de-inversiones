"""Decision log endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from app.governance.decision_log import get_recent_decisions

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
