"""System logs endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query
from loguru import logger

router = APIRouter(prefix="/system/logs", tags=["system"])

LOGS_FILE = Path("data/system_logs.jsonl")


def _read_logs() -> list[dict]:
    if not LOGS_FILE.exists():
        return []
    entries = []
    try:
        with LOGS_FILE.open("r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except OSError:
        logger.exception("Error reading log file %s", LOGS_FILE)
    return entries


def _append_log(level: str, module: str, message: str) -> None:
    try:
        LOGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "module": module,
            "message": message,
        }
        with LOGS_FILE.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        logger.exception("Error appending log entry")


@router.get("")
def list_logs(
    level: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
) -> dict[str, Any]:
    logs = _read_logs()
    if level and level.upper() != "ALL":
        logs = [e for e in logs if e.get("level", "").upper() == level.upper()]
    logs = logs[-limit:]
    return {
        "status": "ok",
        "data": logs,
        "error": None,
        "meta": {"count": len(logs), "total": len(_read_logs())},
    }


@router.post("")
def create_log_entry(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    level = str(payload.get("level", "INFO")).upper()
    module = str(payload.get("module", "api"))
    message = str(payload.get("message", ""))
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    valid_levels = {"INFO", "WARNING", "ERROR", "TRADE", "DEBUG"}
    if level not in valid_levels:
        raise HTTPException(status_code=400, detail=f"Invalid level: {level}")
    _append_log(level, module, message)
    return {"status": "ok", "data": {"logged": True}, "error": None, "meta": {}}


@router.delete("")
def clear_logs() -> dict[str, Any]:
    try:
        if LOGS_FILE.exists():
            LOGS_FILE.unlink()
        return {"status": "ok", "data": {"cleared": True}, "error": None, "meta": {}}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
