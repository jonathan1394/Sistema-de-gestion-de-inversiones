"""Market data storage and retrieval from SQLite for OHLCV candle data."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.data.binance_client import BinanceClient
from app.data.data_validator import INTERVAL_MS, validate_candle_sequence


@dataclass
class DownloadResult:
    symbol: str
    interval: str
    rows_downloaded: int
    validation_errors: list[str]


@dataclass
class Candle:
    symbol: str
    interval: str
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int
    quote_asset_volume: float
    number_of_trades: int
    taker_buy_base_asset_volume: float
    taker_buy_quote_asset_volume: float


def _chunked(seq: list, size: int):
    """Yield successive chunks of *size* from *seq*."""
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def store_klines(connection: sqlite3.Connection, symbol: str, interval: str, klines: list[list]) -> int:
    """Store raw Binance kline data into the candles table. Returns rows inserted."""
    chunk_size = 500

    def _rows(batch: list[list]):
        return [
            (
                symbol.upper(),
                interval,
                int(k[0]),
                float(k[1]),
                float(k[2]),
                float(k[3]),
                float(k[4]),
                float(k[5]),
                int(k[6]),
                float(k[7]),
                int(k[8]),
                float(k[9]),
                float(k[10]),
            )
            for k in batch
        ]

    sql = """
        INSERT OR REPLACE INTO candles (
            symbol,
            interval,
            open_time,
            open,
            high,
            low,
            close,
            volume,
            close_time,
            quote_asset_volume,
            number_of_trades,
            taker_buy_base_asset_volume,
            taker_buy_quote_asset_volume
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    total = 0
    for chunk in _chunked(klines, chunk_size):
        connection.executemany(sql, _rows(chunk))
        connection.commit()
        total += len(chunk)
    return total


def download_and_store(client: BinanceClient, connection: sqlite3.Connection, symbol: str, interval: str, start_time_ms: int | None, end_time_ms: int | None, limit: int) -> DownloadResult:
    """Download a single batch of klines from Binance and store them."""
    klines = client.get_klines(
        symbol=symbol,
        interval=interval,
        start_time_ms=start_time_ms,
        end_time_ms=end_time_ms,
        limit=limit,
    )
    open_times = [int(k[0]) for k in klines]
    errors = validate_candle_sequence(open_times, interval)
    stored = store_klines(connection, symbol, interval, klines)
    return DownloadResult(
        symbol=symbol.upper(),
        interval=interval,
        rows_downloaded=stored,
        validation_errors=errors,
    )


def download_and_store_paginated(client: BinanceClient, connection: sqlite3.Connection, symbol: str, interval: str, start_time_ms: int | None, end_time_ms: int | None, limit: int, max_batches: int | None = None) -> DownloadResult:
    """Download klines in multiple batches with automatic pagination."""
    safe_limit = min(limit, 1000)
    step = INTERVAL_MS.get(interval)
    if step is None:
        raise ValueError(f"Unsupported interval for pagination: {interval}")

    current_start = start_time_ms
    total_rows = 0
    all_open_times: list[int] = []
    batches = 0

    while True:
        if max_batches is not None and batches >= max_batches:
            break

        klines = client.get_klines(
            symbol=symbol,
            interval=interval,
            start_time_ms=current_start,
            end_time_ms=end_time_ms,
            limit=safe_limit,
        )
        if not klines:
            break

        total_rows += store_klines(connection, symbol, interval, klines)
        all_open_times.extend(int(k[0]) for k in klines)
        batches += 1

        last_open = int(klines[-1][0])
        next_start = last_open + step

        if end_time_ms is not None and next_start > end_time_ms:
            break
        if len(klines) < safe_limit:
            break

        current_start = next_start

    errors = validate_candle_sequence(all_open_times, interval)
    return DownloadResult(
        symbol=symbol.upper(),
        interval=interval,
        rows_downloaded=total_rows,
        validation_errors=errors,
    )


def get_candles(connection: sqlite3.Connection, symbol: str, interval: str, start_time_ms: int | None = None, end_time_ms: int | None = None, limit: int | None = None, desc: bool = False) -> list[Candle]:
    """Retrieve candles from the database with optional time range and limit."""
    query = """
        SELECT
            symbol,
            interval,
            open_time,
            open,
            high,
            low,
            close,
            volume,
            close_time,
            quote_asset_volume,
            number_of_trades,
            taker_buy_base_asset_volume,
            taker_buy_quote_asset_volume
        FROM candles
        WHERE symbol = ? AND interval = ?
    """
    params: list[object] = [symbol.upper(), interval]

    if start_time_ms is not None:
        query += " AND open_time >= ?"
        params.append(start_time_ms)
    if end_time_ms is not None:
        query += " AND open_time <= ?"
        params.append(end_time_ms)

    if desc and limit is not None:
        query += " ORDER BY open_time DESC LIMIT ?"
        params.append(limit)
        rows = connection.execute(query, params).fetchall()
        rows.reverse()
    else:
        query += " ORDER BY open_time ASC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = connection.execute(query, params).fetchall()

    return [
        Candle(
            symbol=row["symbol"],
            interval=row["interval"],
            open_time=row["open_time"],
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
            volume=row["volume"],
            close_time=row["close_time"],
            quote_asset_volume=row["quote_asset_volume"],
            number_of_trades=row["number_of_trades"],
            taker_buy_base_asset_volume=row["taker_buy_base_asset_volume"],
            taker_buy_quote_asset_volume=row["taker_buy_quote_asset_volume"],
        )
        for row in rows
    ]
