from __future__ import annotations

from dataclasses import dataclass

RECOMMENDATION_LABELS = {
    "INVERTIR": "INVERTIR",
    "VIGILAR": "VIGILAR",
    "NEUTRAL": "NEUTRAL",
    "EVITAR": "EVITAR",
}

RECOMMENDATION_ORDER = {"INVERTIR": 4, "VIGILAR": 3, "NEUTRAL": 2, "EVITAR": 1}


@dataclass
class Recommendation:
    label: str
    score: float
    confluence: int
    reason: str


def get_recommendation(
    score: float,
    confluence: int = 0,
    invertir_threshold: float = 0.75,
    vigilat_threshold: float = 0.60,
    neutral_threshold: float = 0.40,
    min_confluence_invertir: int = 2,
    min_confluence_vigilat: int = 1,
) -> Recommendation:
    if score >= invertir_threshold and confluence >= min_confluence_invertir:
        return Recommendation(
            label="INVERTIR",
            score=score,
            confluence=confluence,
            reason=f"Score {score:.2f} >= {invertir_threshold}, confluencia {confluence}/{min_confluence_invertir}",
        )
    if score >= invertir_threshold:
        return Recommendation(
            label="VIGILAR",
            score=score,
            confluence=confluence,
            reason=f"Score alto ({score:.2f}) pero confluencia insuficiente ({confluence}/{min_confluence_invertir})",
        )
    if score >= vigilat_threshold and confluence >= min_confluence_vigilat:
        return Recommendation(
            label="VIGILAR",
            score=score,
            confluence=confluence,
            reason=f"Score {score:.2f} >= {vigilat_threshold}, confluencia {confluence}/{min_confluence_vigilat}",
        )
    if score >= neutral_threshold:
        return Recommendation(
            label="NEUTRAL",
            score=score,
            confluence=confluence,
            reason=f"Score {score:.2f} entre {neutral_threshold} y {vigilat_threshold}",
        )
    return Recommendation(
        label="EVITAR",
        score=score,
        confluence=confluence,
        reason=f"Score {score:.2f} por debajo de {neutral_threshold}",
    )


@dataclass
class ProspectScore:
    total: float
    trend_score: float
    volatility_score: float
    volume_score: float
    rsi_score: float
    return_score: float
    breakdown: str


DEFAULT_WEIGHTS: dict[str, float] = {
    "trend": 0.30,
    "volatility": 0.10,
    "volume": 0.15,
    "rsi": 0.15,
    "return": 0.15,
    "signals": 0.15,
}


def validate_weights(weights: dict[str, float]) -> dict[str, float]:
    for key in DEFAULT_WEIGHTS:
        if key not in weights:
            weights[key] = DEFAULT_WEIGHTS[key]
    total = sum(weights.get(k, 0.0) for k in DEFAULT_WEIGHTS)
    if abs(total - 1.0) > 0.01:
        factor = 1.0 / total
        weights = {k: v * factor for k, v in weights.items()}
    return weights


def score_prospect(
    trend: str,
    volatility: str,
    volume_profile: str,
    rsi_condition: str,
    return_pct: float,
    signals_count: int,
    weights: dict[str, float] | None = None,
) -> ProspectScore:
    if weights is None:
        weights = dict(DEFAULT_WEIGHTS)
    else:
        weights = validate_weights(weights)

    trend_scores = {
        "strong_up": 1.0,
        "up": 0.7,
        "sideways": 0.4,
        "down": 0.2,
        "strong_down": 0.1,
    }
    trend_score = trend_scores.get(trend, 0.3)

    volatility_scores = {
        "low": 0.5,
        "moderate": 0.8,
        "high": 0.3,
    }
    volatility_score = volatility_scores.get(volatility, 0.5)

    volume_scores = {
        "high": 0.9,
        "above_average": 0.7,
        "normal": 0.5,
        "unknown": 0.3,
    }
    volume_score = volume_scores.get(volume_profile, 0.3)

    rsi_scores = {
        "oversold": 0.6,
        "neutral": 0.8,
        "overbought": 0.3,
    }
    rsi_score = rsi_scores.get(rsi_condition, 0.5)

    return_score = max(0.0, min(1.0, (return_pct + 20) / 40))

    signal_bonus = min(1.0, signals_count * 0.2)

    total = (
        trend_score * weights["trend"]
        + volatility_score * weights["volatility"]
        + volume_score * weights["volume"]
        + rsi_score * weights["rsi"]
        + return_score * weights["return"]
        + signal_bonus * weights["signals"]
    )

    total = max(0.0, min(1.0, total))

    breakdown_parts = []
    breakdown_parts.append(f"trend={trend_score:.2f}")
    breakdown_parts.append(f"vol={volatility_score:.2f}")
    breakdown_parts.append(f"vol={volume_score:.2f}")
    breakdown_parts.append(f"rsi={rsi_score:.2f}")
    breakdown_parts.append(f"ret={return_score:.2f}")
    breakdown_parts.append(f"sig={signal_bonus:.2f}")

    return ProspectScore(
        total=round(total, 4),
        trend_score=round(trend_score, 4),
        volatility_score=round(volatility_score, 4),
        volume_score=round(volume_score, 4),
        rsi_score=round(rsi_score, 4),
        return_score=round(return_score, 4),
        breakdown=" | ".join(breakdown_parts),
    )
