"""Prospecting package exports for scoring, screening, and storage."""

from app.prospecting.db import (
    add_prospect,
    archive_prospect,
    get_all_prospects,
    get_prospect,
    get_prospects_by_status,
    remove_prospect,
    update_prospect_analysis,
    update_prospect_status,
)
from app.prospecting.screener import ProspectScreener, ProspectScreenerResult
from app.prospecting.scoring import ProspectScore, score_prospect

__all__ = [
    "add_prospect",
    "get_prospect",
    "get_all_prospects",
    "get_prospects_by_status",
    "update_prospect_analysis",
    "update_prospect_status",
    "archive_prospect",
    "remove_prospect",
    "ProspectScreener",
    "ProspectScreenerResult",
    "ProspectScore",
    "score_prospect",
]
