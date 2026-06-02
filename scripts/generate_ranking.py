#!/usr/bin/env python3
"""Generate asset ranking from current market data."""

from __future__ import annotations

import argparse
import logging
from typing import List

from app.config import load_settings
from app.database.connection import get_connection
from app.logging_setup import setup_logging
from app.prospecting.db import get_all_prospects
from app.prospecting.ranking import AssetRanking, generate_ranking

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ranking of assets")
    parser.add_argument(
        "--symbols",
        type=str,
        required=True,
        help="Comma-separated list of symbols (e.g., BTCUSDT,ETHUSDT,SOLUSDT)",
    )
    parser.add_argument(
        "--interval",
        type=str,
        default="1h",
        help="Time interval for analysis (default: 1h)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of top assets to show (default: 10)",
    )
    args = parser.parse_args()

    setup_logging()

    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    settings = load_settings()

    with get_connection(settings.database.path) as conn:
        # Get all prospects (could filter by symbols if needed, but get_all_prospects gets all)
        prospects = get_all_prospects(conn)
        # Filter to only the symbols we're interested in
        prospects = [p for p in prospects if p.symbol in symbols]
        if not prospects:
            logger.info("No prospects found for symbols: %s", symbols)
            return

        # Generate ranking
        rankings: List[AssetRanking] = generate_ranking(prospects)

    print(f"Ranking for {len(symbols)} symbols ({args.interval} interval):")
    print("-" * 80)
    print(f"{'Rank':<4} {'Symbol':<12} {'Score':<6} {'Confluence':<12} {'Recommendation':<15} {'Price':<12} {'1d Return':<10}")
    print("-" * 80)
    for i, rank in enumerate(rankings[: args.limit], 1):
        return_pct = rank.return_pct_1d or 0.0
        print(
            f"{i:<4} {rank.symbol:<12} {rank.score:<6.2f} {rank.confluence:<12} "
            f"{rank.recommendation:<15} ${(rank.price or 0):<11.2f} {return_pct:+.2f}%"
        )


if __name__ == "__main__":
    main()
