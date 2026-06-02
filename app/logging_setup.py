"""Centralized logging configuration for CriptoLab.

Usage:
    from app.logging_setup import setup_logging
    setup_logging()

    # In each module:
    import logging
    logger = logging.getLogger(__name__)
    logger.info("...")
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["plain", "json"]

_FORMAT_PLAIN = "%(asctime)s [%(levelname)-7s] %(name)s | %(message)s"
_FORMAT_JSON = (
    '{"time":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","message":"%(message)s"}'
)


def _resolve_level() -> int:
    raw = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, raw, logging.INFO)


def _resolve_format() -> LogFormat:
    raw = os.getenv("LOG_FORMAT", "plain").lower()
    return "json" if raw == "json" else "plain"


def setup_logging(
    level: int | str | None = None,
    fmt: LogFormat | None = None,
    force: bool = True,
) -> None:
    """Configure the root logger.

    Parameters
    ----------
    level : int or str, optional
        Log level (default: from ``LOG_LEVEL`` env var, else ``INFO``).
    fmt : {"plain", "json"}, optional
        Output format (default: from ``LOG_FORMAT`` env var, else ``plain``).
    force : bool
        Reconfigure even if ``basicConfig`` has already been called.
    """
    if level is None:
        level = _resolve_level()
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    if fmt is None:
        fmt = _resolve_format()

    formatter = logging.Formatter(_FORMAT_PLAIN if fmt == "plain" else _FORMAT_JSON)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    if force:
        root.handlers.clear()
    root.addHandler(handler)
