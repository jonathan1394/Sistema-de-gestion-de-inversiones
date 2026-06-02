"""System endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter


router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "data": {"ok": True}, "error": None, "meta": {}}


@router.get("/status")
def status() -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "status": "ok",
        "data": {"timestamp": now},
        "error": None,
        "meta": {},
    }
