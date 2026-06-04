from __future__ import annotations

import argparse
import sys

from loguru import logger

from app.config import load_settings
from app.data.binance_client import BinanceClient
from app.database.connection import get_connection
from app.database.migrations import run_migrations
from app.logging_setup import setup_logging
from app.prospecting.db import (
    add_prospect,
    archive_prospect,
    get_all_prospects,
    get_prospects_by_status,
    remove_prospect,
)
from app.prospecting.screener import ProspectScreener


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze and track investment prospects")
    sub = parser.add_subparsers(dest="action", required=True)

    p_list = sub.add_parser("list", help="List all prospects")
    p_list.add_argument(
        "--status", default=None, help="Filter by status (watching, active, archived, rejected)"
    )

    p_add = sub.add_parser("add", help="Add a symbol as a prospect")
    p_add.add_argument("--symbol", required=True, help="Symbol like BTCUSDT")
    p_add.add_argument("--interval", default="1d", help="Analysis interval (default: 1d)")
    p_add.add_argument("--notes", default="", help="Optional notes")

    p_remove = sub.add_parser("remove", help="Remove a prospect")
    p_remove.add_argument("--symbol", required=True, help="Symbol like BTCUSDT")
    p_remove.add_argument("--interval", default="1d", help="Interval")

    p_archive = sub.add_parser("archive", help="Archive a prospect")
    p_archive.add_argument("--symbol", required=True, help="Symbol like BTCUSDT")
    p_archive.add_argument("--interval", default="1d", help="Interval")

    p_scan = sub.add_parser("scan", help="Run screening analysis on all or a specific prospect")
    p_scan.add_argument("--symbol", default=None, help="Specific symbol to scan (optional)")
    p_scan.add_argument("--interval", default="1d", help="Interval")
    p_scan.add_argument(
        "--download", action="store_true", default=True, help="Download data if missing"
    )
    p_scan.add_argument("--limit", type=int, default=200, help="Max candles to analyze")

    p_report = sub.add_parser("report", help="Generate a screening report")

    p_scan_all = sub.add_parser("scan-all", help="Run screening on all prospects")
    p_scan_all.add_argument(
        "--download", action="store_true", default=True, help="Download data if missing"
    )
    p_scan_all.add_argument("--limit", type=int, default=200, help="Max candles to analyze")
    p_scan_all.add_argument("--settings", default="settings.yaml", help="Path to settings YAML")
    return parser.parse_args()


def _make_screener(args: argparse.Namespace) -> ProspectScreener:
    config = load_settings(getattr(args, "settings", "settings.yaml"))
    client = BinanceClient(config.binance)
    connection = get_connection(config.database.path)
    run_migrations(connection)
    return ProspectScreener(
        client=client,
        connection=connection,
        download_if_missing=args.download,
        limit_candles=args.limit,
    )


def _make_connection(settings_path: str = "settings.yaml"):
    config = load_settings(settings_path)
    conn = get_connection(config.database.path)
    run_migrations(conn)
    return conn, config


def cmd_list(args: argparse.Namespace) -> None:
    conn, _ = _make_connection()
    if args.status:
        prospects = get_prospects_by_status(conn, args.status)
    else:
        prospects = get_all_prospects(conn)
    if not prospects:
        logger.info("No prospects found.")
        return
    print(
        f"{'Symbol':12s} {'Interval':6s} {'Status':10s} {'Score':>6s}  {'Trend':14s} {'Signals':>7s}  {'Last Analysis':16s}"
    )
    print("-" * 75)
    for p in prospects:
        last = str(p.last_analysis_at) if p.last_analysis_at else "-"
        print(
            f"{p.symbol:12s} {p.interval:6s} {p.status:10s} {p.score:>6.2f}  {str(p.trend or '-'):14s} {p.signals_count:>7d}  {last:16s}"
        )


def cmd_add(args: argparse.Namespace) -> None:
    conn, _ = _make_connection()
    existing = add_prospect(conn, args.symbol, args.interval, notes=args.notes)
    if existing.last_analysis_at is None:
        logger.info("Added %s (%s) as a prospect.", args.symbol, args.interval)
    else:
        logger.info("%s (%s) already in prospects.", args.symbol, args.interval)


def cmd_remove(args: argparse.Namespace) -> None:
    conn, _ = _make_connection()
    if remove_prospect(conn, args.symbol, args.interval):
        logger.info("Removed %s (%s) from prospects.", args.symbol, args.interval)
    else:
        logger.info("%s (%s) not found in prospects.", args.symbol, args.interval)


def cmd_archive(args: argparse.Namespace) -> None:
    conn, _ = _make_connection()
    archive_prospect(conn, args.symbol, args.interval)
    logger.info("Archived %s (%s).", args.symbol, args.interval)


def cmd_scan(args: argparse.Namespace) -> None:
    screener = _make_screener(args)
    if args.symbol:
        result = screener.run_on_symbol(args.symbol, args.interval)
        if result is None:
            logger.warning(
                "Could not screen %s (%s) — insufficient data.", args.symbol, args.interval
            )
            return
        assets = [result]
    else:
        result = screener.run_on_all()
        assets = result.assets
    _print_results(assets)


def cmd_report(args: argparse.Namespace) -> None:
    conn, _ = _make_connection()
    prospects = get_all_prospects(conn)
    if not prospects:
        logger.info("No prospects in database. Add some with `add` first.")
        return

    watching = [p for p in prospects if p.status == "watching"]
    active = [p for p in prospects if p.status == "active"]
    archived = [p for p in prospects if p.status == "archived"]

    print("\nProspect Report")
    print(f"{'=' * 50}")
    print(f"Total prospects: {len(prospects)}")
    print(f"  Watching: {len(watching)}")
    print(f"  Active:   {len(active)}")
    print(f"  Archived: {len(archived)}")
    print()

    if prospects:
        top = max(prospects, key=lambda p: p.score)
        print(f"Top prospect: {top.symbol} ({top.interval}) — score: {top.score:.4f}")


def _print_results(assets) -> None:
    if not assets:
        logger.info("No assets screened.")
        return
    print(
        f"\n{'Symbol':12s} {'Score':>6s} {'Return':>7s} {'Vol':>5s} {'Trend':14s} {'Signals':>7s}"
    )
    print("-" * 55)
    for a in assets:
        print(
            f"{a.symbol:12s} {a.score.total:>6.3f} {a.return_pct:>+6.2f}% {a.volatility:>5s} {a.trend:14s} {a.strategy_signals:>7d}"
        )
    print()


def main() -> None:
    args = parse_args()
    setup_logging()

    action_map = {
        "list": cmd_list,
        "add": cmd_add,
        "remove": cmd_remove,
        "archive": cmd_archive,
        "scan": cmd_scan,
        "scan-all": cmd_scan,
        "report": cmd_report,
    }

    handler = action_map.get(args.action)
    if handler:
        handler(args)
    else:
        logger.error("Unknown action: %s", args.action)
        sys.exit(1)


if __name__ == "__main__":
    main()
