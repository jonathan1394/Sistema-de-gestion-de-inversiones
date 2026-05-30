from __future__ import annotations

from typing import Iterable


INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


def validate_candle_sequence(open_times: Iterable[int], interval: str) -> list[str]:
    errors: list[str] = []
    times = list(open_times)
    if not times:
        return ["No candles returned"]

    if interval not in INTERVAL_MS:
        return [f"Unsupported interval: {interval}"]

    step = INTERVAL_MS[interval]

    for index in range(1, len(times)):
        expected = times[index - 1] + step
        if times[index] != expected:
            errors.append(
                f"Gap or overlap detected between {times[index - 1]} and {times[index]}"
            )

    if len(times) != len(set(times)):
        errors.append("Duplicate candle open_time values detected")

    return errors
