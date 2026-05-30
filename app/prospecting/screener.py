from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from app.ai.market_summary import generate_market_summary
from app.data.binance_client import BinanceClient
from app.data.market_data import download_and_store, get_candles
from app.prospecting.db import (
    add_prospect,
    get_all_prospects,
    update_prospect_analysis,
)
from app.prospecting.scoring import ProspectScore, score_prospect
from app.strategies.base_strategy import BaseStrategy
from app.strategies.moving_average import MovingAverageCrossover
from app.strategies.rsi_strategy import RSIStrategy
from app.strategies.trend_following import TrendFollowing


@dataclass
class ScreenedAsset:
    symbol: str
    interval: str
    score: ProspectScore
    candles_analyzed: int
    return_pct: float
    volatility_pct: float
    avg_volume: float
    trend: str
    volatility: str
    volume_profile: str
    rsi_condition: str
    strategy_signals: int
    summary: str


@dataclass
class ProspectScreenerResult:
    assets: list[ScreenedAsset] = field(default_factory=list)

    @property
    def top(self) -> Optional[ScreenedAsset]:
        return self.assets[0] if self.assets else None

    @property
    def count(self) -> int:
        return len(self.assets)


class ProspectScreener:
    def __init__(
        self,
        client: BinanceClient,
        connection: sqlite3.Connection,
        download_if_missing: bool = True,
        limit_candles: int = 200,
        weights: dict[str, float] | None = None,
    ) -> None:
        self._client = client
        self._connection = connection
        self._download_if_missing = download_if_missing
        self._limit_candles = limit_candles
        self._weights = weights
        self._strategies: list[BaseStrategy] = [
            MovingAverageCrossover(parameters={"fast_period": 20, "slow_period": 50}),
            RSIStrategy(parameters={"rsi_period": 14, "oversold": 30, "overbought": 70}),
            TrendFollowing(parameters={"ema_long": 200, "ema_fast": 20, "ema_slow": 50}),
        ]

    def run_on_all(self) -> ProspectScreenerResult:
        prospects = get_all_prospects(self._connection)
        result = ProspectScreenerResult()
        for p in prospects:
            screened = self._screen_one(p.symbol, p.interval)
            if screened is not None:
                result.assets.append(screened)
                update_prospect_analysis(
                    connection=self._connection,
                    symbol=p.symbol,
                    interval=p.interval,
                    score=screened.score.total,
                    trend=screened.trend,
                    volatility=screened.volatility,
                    volume_profile=screened.volume_profile,
                    rsi_condition=screened.rsi_condition,
                    signals_count=screened.strategy_signals,
                    metadata={
                        "return_pct": screened.return_pct,
                        "volatility_pct": screened.volatility_pct,
                        "avg_volume": screened.avg_volume,
                        "candles_analyzed": screened.candles_analyzed,
                        "breakdown": screened.score.breakdown,
                    },
                )
        result.assets.sort(key=lambda a: a.score.total, reverse=True)
        return result

    def run_on_symbol(
        self,
        symbol: str,
        interval: str = "1d",
    ) -> Optional[ScreenedAsset]:
        screened = self._screen_one(symbol, interval)
        if screened is not None:
            update_prospect_analysis(
                connection=self._connection,
                symbol=symbol,
                interval=interval,
                score=screened.score.total,
                trend=screened.trend,
                volatility=screened.volatility,
                volume_profile=screened.volume_profile,
                rsi_condition=screened.rsi_condition,
                signals_count=screened.strategy_signals,
                metadata={
                    "return_pct": screened.return_pct,
                    "volatility_pct": screened.volatility_pct,
                    "avg_volume": screened.avg_volume,
                    "candles_analyzed": screened.candles_analyzed,
                    "breakdown": screened.score.breakdown,
                },
            )
            add_prospect(self._connection, symbol, interval)
        return screened

    def _screen_one(
        self,
        symbol: str,
        interval: str,
    ) -> Optional[ScreenedAsset]:
        candles = self._load_candles(symbol, interval)
        if candles is None or len(candles) < 50:
            return None

        data = self._candles_to_dataframe(candles)
        if data.empty:
            return None

        try:
            summary = generate_market_summary(data, symbol=symbol, period=interval)
        except (ValueError, KeyError):
            return None

        strategy_signals = set()
        for strategy in self._strategies:
            try:
                result = strategy.generate_signals(data)
                for sig in result.signals:
                    if sig.action in ("BUY", "SELL"):
                        strategy_signals.add(f"{sig.action}_{type(strategy).__name__}")
            except Exception:
                continue

        score = score_prospect(
            trend=summary.condition.trend,
            volatility=summary.condition.volatility,
            volume_profile=summary.condition.volume_profile,
            rsi_condition=summary.condition.rsi_condition,
            return_pct=summary.return_pct,
            signals_count=len(strategy_signals),
            weights=self._weights,
        )

        return ScreenedAsset(
            symbol=symbol.upper(),
            interval=interval,
            score=score,
            candles_analyzed=len(candles),
            return_pct=summary.return_pct,
            volatility_pct=summary.volatility_pct,
            avg_volume=summary.avg_volume,
            trend=summary.condition.trend,
            volatility=summary.condition.volatility,
            volume_profile=summary.condition.volume_profile,
            rsi_condition=summary.condition.rsi_condition,
            strategy_signals=len(strategy_signals),
            summary=summary.condition.summary,
        )

    def _load_candles(
        self,
        symbol: str,
        interval: str,
    ) -> Optional[list]:
        candles = get_candles(
            connection=self._connection,
            symbol=symbol,
            interval=interval,
            limit=self._limit_candles,
            desc=True,
        )
        if candles and len(candles) >= 50:
            return candles

        if not self._download_if_missing:
            return None

        try:
            result = download_and_store(
                client=self._client,
                connection=self._connection,
                symbol=symbol,
                interval=interval,
                start_time_ms=None,
                end_time_ms=None,
                limit=min(self._limit_candles, 1000),
            )
            if result.rows_downloaded < 50:
                return None
        except Exception:
            return None

        candles = get_candles(
            connection=self._connection,
            symbol=symbol,
            interval=interval,
            limit=self._limit_candles,
            desc=True,
        )
        return candles if len(candles) >= 50 else None

    def _candles_to_dataframe(self, candles: list) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "timestamp": pd.to_datetime(
                    [c.open_time for c in candles], unit="ms", utc=True
                ),
                "open": [c.open for c in candles],
                "high": [c.high for c in candles],
                "low": [c.low for c in candles],
                "close": [c.close for c in candles],
                "volume": [c.volume for c in candles],
            }
        )
