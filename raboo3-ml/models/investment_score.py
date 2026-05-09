"""Heuristic investment scoring and recommendation.

This is *not* an ML model (for now) but a deterministic scoring
function that combines:

- expected annual growth rate (fraction, e.g. 0.05 for 5%)
- gross rent yield (fraction, e.g. 0.06 for 6% per year)
- liquidity score (0..1), e.g. from transaction volume

into:
    - score (0..100)
    - recommendation label: strong_buy / buy / hold / avoid
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InvestmentSummary:
    score: float
    label: str
    growth_rate: float
    rent_yield: float
    liquidity: float


def _normalize_growth(growth: float) -> float:
    """Map growth [-10%, 20%] to [0, 1]."""
    lo, hi = -0.10, 0.20
    if growth <= lo:
        return 0.0
    if growth >= hi:
        return 1.0
    return (growth - lo) / (hi - lo)


def _normalize_yield(y: float) -> float:
    """Map yield [0%, 10%] to [0, 1]."""
    lo, hi = 0.00, 0.10
    if y <= lo:
        return 0.0
    if y >= hi:
        return 1.0
    return (y - lo) / (hi - lo)


def _normalize_liquidity(liq: float) -> float:
    """Assume liq already in [0, 1], clamp for safety."""
    if liq <= 0.0:
        return 0.0
    if liq >= 1.0:
        return 1.0
    return liq


def compute_investment_score(
    growth_rate: float,
    rent_yield: float,
    liquidity: float,
) -> InvestmentSummary:
    """Combine growth, yield, and liquidity into a 0..100 score + label."""
    g_norm = _normalize_growth(growth_rate)
    y_norm = _normalize_yield(rent_yield)
    l_norm = _normalize_liquidity(liquidity)

    # weights: growth 40%, yield 40%, liquidity 20%
    score_0_1 = 0.4 * g_norm + 0.4 * y_norm + 0.2 * l_norm
    score = score_0_1 * 100.0

    if score >= 80:
        label = "strong_buy"
    elif score >= 60:
        label = "buy"
    elif score >= 40:
        label = "hold"
    else:
        label = "avoid"

    return InvestmentSummary(
        score=round(score, 2),
        label=label,
        growth_rate=growth_rate,
        rent_yield=rent_yield,
        liquidity=l_norm,
    )

