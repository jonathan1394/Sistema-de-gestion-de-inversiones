"""Shared Pydantic schemas for API responses."""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiError(BaseModel):
    message: str
    type: str | None = None
    details: dict[str, Any] | None = None


class ApiResponse(BaseModel, Generic[T]):
    status: str
    data: Optional[T] = None
    error: Optional[ApiError] = None
    meta: dict[str, Any] = {}
