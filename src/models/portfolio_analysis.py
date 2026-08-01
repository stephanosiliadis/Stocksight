from __future__ import annotations

from pydantic import BaseModel, Field


class PortfolioAnalysis(BaseModel):
    """
    Computed analytics for a Portfolio at a point in time.

    Attributes:
        total_value: Current market value of all holdings combined.
        total_cost: Total amount originally paid for all holdings
            (shares * cost_basis, summed).
        total_return_pct: (total_value - total_cost) / total_cost * 100.
        allocation: Each holding ticker's percentage share of
            total_value (sums to ~100 across all holdings).
        sector_allocation: Each sector's percentage share of
            total_value, aggregated across holdings sharing that sector
            (sums to ~100).
        diversification_score: 1 - Herfindahl index of allocation
            weights (as fractions). Roughly 0 (fully concentrated in one
            holding) to just under 1 (evenly spread across many).
        benchmark_return_pct: The benchmark's (e.g. SPY) return over the
            same period, from RelativeStrengthService -- None if no
            benchmark data was available.
    """

    total_value: float
    total_cost: float
    total_return_pct: float
    allocation: dict[str, float] = Field(default_factory=dict)
    sector_allocation: dict[str, float] = Field(default_factory=dict)
    diversification_score: float
    benchmark_return_pct: float | None = None
