"""Asset ranking module for generating investment recommendations."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import List, Optional

from app.config import AppConfig, load_settings
from app.database.connection import get_connection
from app.prospecting.db import Prospect
from app.prospecting.market_decision import analyze_timeframe, compute_confluence
from app.prospecting.scoring import get_recommendation

logger = logging.getLogger(__name__)

@dataclass
class AssetRanking:
    """Ranked asset with recommendation and supporting data."""

    symbol: str
    score: float
    confluence: int
    recommendation: str  # INVERTIR, VIGILAR, NEUTRAL, EVITAR
    reason: str
    trend_1h: Optional[str] = None
    trend_4h: Optional[str] = None
    trend_1d: Optional[str] = None
    price: Optional[float] = None
    return_pct_1d: Optional[float] = None


def generate_ranking(
    prospects: List[Prospect],
    settings: AppConfig | None = None,
    conn: sqlite3.Connection | None = None,
) -> List[AssetRanking]:
    """Generate a ranked list of assets from prospects.

    Parameters
    ----------
    prospects : List[Prospect]
        List of prospect objects (from database).

    Returns
    -------
    List[AssetRanking]
        List of ranked assets, sorted by score descending.
    """
    settings = settings or load_settings()
    conn = conn or get_connection(settings.database.path)
    recommendation_cfg = settings.prospecting.get("recommendation", {})

    rankings: List[AssetRanking] = []
    for prospect in prospects:
        # Analyze multiple timeframes for confluence and trend
        tf_1h = analyze_timeframe(conn, prospect.symbol, "1h")
        tf_4h = analyze_timeframe(conn, prospect.symbol, "4h")
        tf_1d = analyze_timeframe(conn, prospect.symbol, "1d")

        # Get current price (prefer 1h, then 4h, then 1d)
        price: Optional[float] = None
        return_pct_1d: Optional[float] = None
        for tf in [tf_1h, tf_4h, tf_1d]:
            if tf and tf.get("price") is not None:
                price = tf["price"]
                if tf is tf_1d:
                    return_pct_1d = tf.get("return_pct")
                break

        # Compute confluence from available timeframes
        tf_results = [tf for tf in [tf_1h, tf_4h, tf_1d] if tf is not None]
        confluence = compute_confluence(tf_results)

        # Get recommendation using the scoring function (which uses thresholds from settings)
        recommendation_obj = get_recommendation(
            score=prospect.score,
            confluence=confluence,
            invertir_threshold=recommendation_cfg.get("invertir_threshold", 0.75),
            vigilat_threshold=recommendation_cfg.get("vigilar_threshold", 0.60),
            neutral_threshold=recommendation_cfg.get("neutral_threshold", 0.40),
            min_confluence_invertir=recommendation_cfg.get("min_confluence_for_invertir", 2),
            min_confluence_vigilat=recommendation_cfg.get("min_confluence_for_vigilar", 1),
        )

        # Build reason string
        reason_parts = [
            f"Score {prospect.score:.2f}",
            f"Confluencia {confluence}/3",
        ]
        if tf_1d:
            reason_parts.append(f"Retorno 1d {tf_1d.get('return_pct', 0):+.2f}%")
        if tf_1h:
            reason_parts.append(f"Tendencia 1h: {tf_1h.get('trend', 'N/A')}")
        if tf_4h:
            reason_parts.append(f"Tendencia 4h: {tf_4h.get('trend', 'N/A')}")
        if tf_1d:
            reason_parts.append(f"Tendencia 1d: {tf_1d.get('trend', 'N/A')}")

        reason = " | ".join(reason_parts)

        rankings.append(
            AssetRanking(
                symbol=prospect.symbol,
                score=prospect.score,
                confluence=confluence,
                recommendation=recommendation_obj.label,
                reason=reason,
                trend_1h=tf_1h.get("trend") if tf_1h else None,
                trend_4h=tf_4h.get("trend") if tf_4h else None,
                trend_1d=tf_1d.get("trend") if tf_1d else None,
                price=price,
                return_pct_1d=return_pct_1d,
            )
        )

    # Sort by score descending
    rankings.sort(key=lambda x: x.score, reverse=True)
    return rankings
