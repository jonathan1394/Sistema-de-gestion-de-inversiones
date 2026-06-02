"""Configuration endpoints."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Request


router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
def get_config(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    return {"status": "ok", "data": asdict(settings), "error": None, "meta": {}}
