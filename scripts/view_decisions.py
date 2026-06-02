#!/usr/bin/env python3
"""View decision log from the database."""

from __future__ import annotations

import argparse
from datetime import datetime
from typing import List

from app.config import load_settings
from app.database.connection import get_connection
from app.governance.decision_log import get_recent_decisions


def format_decision(d) -> str:
    """Format a decision for display."""
    dt = d.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    approved = "✅ APROBADA" if d.approved else "❌ RECHAZADA"
    return f"[{dt}] {d.symbol} {d.decision_type}: {approved} - {d.reason}"


def main() -> None:
    parser = argparse.ArgumentParser(description="View decision log")
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of recent decisions to show (default: 20)",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        help="Filter by symbol (e.g., BTCUSDT)",
    )
    parser.add_argument(
        "--approved",
        action="store_true",
        help="Show only approved decisions",
    )
    parser.add_argument(
        "--rejected",
        action="store_true",
        help="Show only rejected decisions",
    )
    args = parser.parse_args()

    settings = load_settings()
    with get_connection(settings.database.path) as conn:
        decisions = get_recent_decisions(
            limit=args.limit,
            symbol=args.symbol,
            approved_only=args.approved,
            rejected_only=args.rejected,
        )

    if not decisions:
        print("No decisions found matching criteria.")
        return

    print(f"Showing {len(decisions)} recent decision(s):")
    print("-" * 80)
    for d in decisions:
        print(format_decision(d))


if __name__ == "__main__":
    main()