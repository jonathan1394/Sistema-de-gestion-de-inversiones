"""Alerts endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Query, Request

from app.alerts.channels import HISTORY_FILE, AlertManager, build_alert_manager

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/history")
def history(request: Request, limit: int = Query(default=100, ge=1, le=5000)) -> dict[str, Any]:
    s = request.app.state.settings
    manager: AlertManager = build_alert_manager(s.alerts if isinstance(s.alerts, dict) else None)
    items = manager.get_history(limit=limit)
    return {"status": "ok", "data": items, "error": None, "meta": {"count": len(items)}}


@router.get("/rules")
def rules(request: Request) -> dict[str, Any]:
    s = request.app.state.settings
    rules_cfg = (s.alerts or {}).get("rules", {}) if isinstance(s.alerts, dict) else {}
    return {"status": "ok", "data": rules_cfg, "error": None, "meta": {}}


@router.post("/rules")
def update_rules(_: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    # MVP: rule persistence is not implemented; accept payload for UI prototyping.
    return {
        "status": "ok",
        "data": {"accepted": True, "note": "Rule persistence not implemented", "payload": payload},
        "error": None,
        "meta": {},
    }


@router.post("/history/clear")
def clear_history(_: Request) -> dict[str, Any]:
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
    return {"status": "ok", "data": {"cleared": True}, "error": None, "meta": {}}
