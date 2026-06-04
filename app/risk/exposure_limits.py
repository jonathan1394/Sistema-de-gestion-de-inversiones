"""Portfolio exposure checks used before opening new positions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExposureCheckResult:
    approved: bool = True
    current_asset_exposure_pct: float = 0.0
    current_total_exposure_pct: float = 0.0
    proposed_additional_pct: float = 0.0
    asset_exposure_after_pct: float = 0.0
    total_exposure_after_pct: float = 0.0
    max_asset_pct: float = 0.35
    max_total_pct: float = 0.50
    max_altcoin_pct: float = 0.40
    rejection_reason: str = ""


@dataclass
class PortfolioState:
    total_capital: float = 0.0
    cash: float = 0.0
    positions: dict[str, float] = field(default_factory=dict)
    asset_classes: dict[str, str] = field(default_factory=dict)


def check_exposure(
    portfolio: PortfolioState,
    symbol: str,
    trade_value: float,
    max_asset_pct: float = 0.35,
    max_total_pct: float = 0.50,
    max_altcoin_pct: float = 0.40,
    altcoin_symbols: set[str] | None = None,
) -> ExposureCheckResult:
    """Validate asset, total, and optional altcoin exposure limits.

    Exposure is based on gross (absolute) position values so that short
    positions are correctly bounded.
    """
    if portfolio.total_capital <= 0:
        return ExposureCheckResult(
            approved=False,
            rejection_reason="Total capital must be positive",
        )

    current_asset_value = abs(portfolio.positions.get(symbol, 0.0))
    current_asset_exposure = current_asset_value / portfolio.total_capital
    gross_exposure = sum(abs(v) for v in portfolio.positions.values())
    current_total_exposure = gross_exposure / portfolio.total_capital

    proposed_additional = trade_value / portfolio.total_capital
    asset_after = current_asset_exposure + proposed_additional
    total_after = current_total_exposure + proposed_additional

    if asset_after > max_asset_pct:
        return ExposureCheckResult(
            approved=False,
            current_asset_exposure_pct=current_asset_exposure * 100,
            current_total_exposure_pct=current_total_exposure * 100,
            proposed_additional_pct=proposed_additional * 100,
            asset_exposure_after_pct=asset_after * 100,
            total_exposure_after_pct=total_after * 100,
            max_asset_pct=max_asset_pct,
            rejection_reason=(f"Asset exposure {asset_after:.1%} exceeds max {max_asset_pct:.0%}"),
        )

    if total_after > max_total_pct:
        return ExposureCheckResult(
            approved=False,
            current_asset_exposure_pct=current_asset_exposure * 100,
            current_total_exposure_pct=current_total_exposure * 100,
            proposed_additional_pct=proposed_additional * 100,
            asset_exposure_after_pct=asset_after * 100,
            total_exposure_after_pct=total_after * 100,
            max_total_pct=max_total_pct,
            rejection_reason=(f"Total exposure {total_after:.1%} exceeds max {max_total_pct:.0%}"),
        )

    if altcoin_symbols and symbol in altcoin_symbols:
        altcoin_exposure = _calc_altcoin_exposure(portfolio, altcoin_symbols)
        altcoin_after = altcoin_exposure + proposed_additional
        if altcoin_after > max_altcoin_pct:
            return ExposureCheckResult(
                approved=False,
                current_asset_exposure_pct=current_asset_exposure * 100,
                current_total_exposure_pct=current_total_exposure * 100,
                proposed_additional_pct=proposed_additional * 100,
                asset_exposure_after_pct=asset_after * 100,
                total_exposure_after_pct=total_after * 100,
                max_altcoin_pct=max_altcoin_pct,
                rejection_reason=(
                    f"Altcoin exposure {altcoin_after:.1%} exceeds max {max_altcoin_pct:.0%}"
                ),
            )

    return ExposureCheckResult(
        approved=True,
        current_asset_exposure_pct=current_asset_exposure * 100,
        current_total_exposure_pct=current_total_exposure * 100,
        proposed_additional_pct=proposed_additional * 100,
        asset_exposure_after_pct=asset_after * 100,
        total_exposure_after_pct=total_after * 100,
        max_asset_pct=max_asset_pct,
        max_total_pct=max_total_pct,
    )


def _calc_altcoin_exposure(portfolio: PortfolioState, altcoin_set: set[str]) -> float:
    """Return current total altcoin exposure as a capital fraction (gross)."""
    altcoin_value = sum(
        abs(value) for sym, value in portfolio.positions.items() if sym in altcoin_set
    )
    return altcoin_value / portfolio.total_capital if portfolio.total_capital > 0 else 0.0
