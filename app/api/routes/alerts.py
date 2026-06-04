"""Alerts endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Query, Request

from app.alerts.channels import HISTORY_FILE, AlertManager, build_alert_manager

router = APIRouter(prefix="/alerts", tags=["alerts"])
RULES_FILE = Path("data/alert_rules.json")


def _load_persisted_rules() -> dict[str, Any]:
    if not RULES_FILE.exists():
        return {}
    try:
        with RULES_FILE.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _store_rules(rules_cfg: dict[str, Any]) -> None:
    RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RULES_FILE.open("w", encoding="utf-8") as handle:
        json.dump(rules_cfg, handle, indent=2, sort_keys=True)


def _current_rules(settings_alerts: Any) -> dict[str, Any]:
    base_rules = (settings_alerts or {}).get("rules", {}) if isinstance(settings_alerts, dict) else {}
    persisted_rules = _load_persisted_rules()
    return persisted_rules or base_rules


@router.get("/history")
def history(request: Request, limit: int = Query(default=100, ge=1, le=5000)) -> dict[str, Any]:
    s = request.app.state.settings
    manager: AlertManager = build_alert_manager(s.alerts if isinstance(s.alerts, dict) else None)
    items = manager.get_history(limit=limit)
    return {"status": "ok", "data": items, "error": None, "meta": {"count": len(items)}}


@router.get("/rules")
def rules(request: Request) -> dict[str, Any]:
    s = request.app.state.settings
    rules_cfg = _current_rules(s.alerts)
    return {"status": "ok", "data": rules_cfg, "error": None, "meta": {}}


@router.post("/rules")
def update_rules(_: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}
    _store_rules(payload)
    return {
        "status": "ok",
        "data": {"updated": True, "rules": payload},
        "error": None,
        "meta": {},
    }


@router.post("/history/clear")
def clear_history(_: Request) -> dict[str, Any]:
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
    return {"status": "ok", "data": {"cleared": True}, "error": None, "meta": {}}
