from __future__ import annotations

import argparse

from loguru import logger

from app.config import load_settings
from app.data.binance_client import BinanceClient
from app.data.market_data import download_and_store, download_and_store_paginated
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.logging_setup import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download historical candles from Binance")
    parser.add_argument("--symbol", required=True, help="Symbol like BTCUSDT")
    parser.add_argument("--interval", required=True, help="Kline interval like 1h, 4h, 1d")
    parser.add_argument("--start-ms", type=int, default=None, help="Start time in ms")
    parser.add_argument("--end-ms", type=int, default=None, help="End time in ms")
    parser.add_argument("--limit", type=int, default=1000, help="Rows per request (max 1000)")
    parser.add_argument(
        "--paginate",
        action="store_true",
        help="Download multiple batches until reaching end time or data end",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Safety cap for paginated requests",
    )
    parser.add_argument(
        "--settings",
        default="settings.yaml",
        help="Path to settings YAML",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_settings(args.settings)
    setup_logging()

    if config.mode not in {"analysis", "backtest", "paper"}:
        raise RuntimeError(f"Unsafe mode for downloader: {config.mode}")

    client = BinanceClient(config.binance)
    connection = get_connection(config.database.path)
    run_migrations(connection)

    if args.paginate:
        result = download_and_store_paginated(
            client=client,
            connection=connection,
            symbol=args.symbol,
            interval=args.interval,
            start_time_ms=args.start_ms,
            end_time_ms=args.end_ms,
            limit=min(args.limit, 1000),
            max_batches=args.max_batches,
        )
    else:
        result = download_and_store(
            client=client,
            connection=connection,
            symbol=args.symbol,
            interval=args.interval,
            start_time_ms=args.start_ms,
            end_time_ms=args.end_ms,
            limit=min(args.limit, 1000),
        )

    logger.info(
        "Downloaded %d rows for %s %s", result.rows_downloaded, result.symbol, result.interval
    )
    if result.validation_errors:
        logger.warning("Validation warnings:")
        for warning in result.validation_errors:
            logger.warning("- %s", warning)


if __name__ == "__main__":
    main()
