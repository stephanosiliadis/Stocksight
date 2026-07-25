from __future__ import annotations

from pydantic import BaseModel


class AnalystRating(BaseModel):
    """
    Aggregated analyst sentiment for a ticker.

    Attributes:
        consensus: Majority-vote rating label derived from the analyst
            recommendation breakdown (e.g. "Buy", "Hold", "Strong Sell"),
            or "No Rating" when no recommendation counts are available.
        num_analysts: Total number of analysts contributing to the
            recommendation breakdown. 0 when unavailable.
        price_target_mean: Mean analyst price target, if available.
        price_target_high: Highest analyst price target, if available.
        price_target_low: Lowest analyst price target, if available.
    """

    consensus: str
    num_analysts: int
    price_target_mean: float | None = None
    price_target_high: float | None = None
    price_target_low: float | None = None
