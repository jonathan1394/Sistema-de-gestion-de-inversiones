"""Decision logging utilities for audit trail.

Provides functions to log decisions to the decision_log table and
retrieve them if needed.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.config import AppConfig, load_settings
from app.database.connection import get_connection


@dataclass
class DecisionLogEntry:
    """Decision log entry."""

    decision_id: str
    decision_type: str
    timestamp: str
    symbol: Optional[str]
    strategy_name: Optional[str]
    timeframe: Optional[str]
    mode: str
    approved: bool
    reason: str
    input_json: Dict[str, Any]
    output_json: Dict[str, Any]
    policy_version: Optional[str] = None
    strategy_version: Optional[str] = None


def log_decision(
    *,
    decision_type: str,
    symbol: Optional[str] = None,
    strategy_name: Optional[str] = None,
    timeframe: Optional[str] = None,
    mode: str,
    approved: bool,
    reason: str,
    input_data: Optional[Dict[str, Any]] = None,
    output_data: Optional[Dict[str, Any]] = None,
    policy_version: Optional[str] = None,
    strategy_version: Optional[str] = None,
    settings: AppConfig | None = None,
) -> str:
    """Log a decision to the decision_log table.

    Returns the generated decision_id.
    """
    settings = settings or load_settings()
    conn = get_connection(settings.database.path)

    decision_id = str(uuid.uuid4())
    timestamp = str(int(time.time() * 1000))  # milliseconds UTC

    input_json = json.dumps(input_data or {})
    output_json = json.dumps(output_data or {})

    conn.execute(
        """
        INSERT INTO decision_log (
            decision_id,
            decision_type,
            timestamp,
            symbol,
            strategy_name,
            timeframe,
            mode,
            approved,
            reason,
            input_json,
            output_json,
            policy_version,
            strategy_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            decision_id,
            decision_type,
            timestamp,
            symbol,
            strategy_name,
            timeframe,
            mode,
            1 if approved else 0,
            reason,
            input_json,
            output_json,
            policy_version,
            strategy_version,
        ),
    )
    conn.commit()
    return decision_id


def get_recent_decisions(
    limit: int = 50,
    symbol: Optional[str] = None,
    approved_only: bool = False,
    rejected_only: bool = False,
    settings: AppConfig | None = None,
) -> List[DecisionLogEntry]:
    """Retrieve recent decisions from the decision_log table with optional filtering."""
    settings = settings or load_settings()
    conn = get_connection(settings.database.path)
    conn.row_factory = sqlite3.Row

    # Build query with optional filters
    query = "SELECT * FROM decision_log"
    params: List[Any] = []

    conditions = []
    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol)
    if approved_only:
        conditions.append("approved = 1")
    if rejected_only:
        conditions.append("approved = 0")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    decisions: List[DecisionLogEntry] = []
    for row in rows:
        decisions.append(
            DecisionLogEntry(
                decision_id=row["decision_id"],
                decision_type=row["decision_type"],
                timestamp=row["timestamp"],
                symbol=row["symbol"],
                strategy_name=row["strategy_name"],
                timeframe=row["timeframe"],
                mode=row["mode"],
                approved=bool(row["approved"]),
                reason=row["reason"],
                input_json=json.loads(row["input_json"] or "{}"),
                output_json=json.loads(row["output_json"] or "{}"),
                policy_version=row["policy_version"],
                strategy_version=row["strategy_version"],
            )
        )
    return decisions
