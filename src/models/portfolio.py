from __future__ import annotations

from pydantic import BaseModel, Field

from src.models.holding import Holding


class Portfolio(BaseModel):
    """
    A named collection of actual Holdings.

    Deliberately separate from a watchlist: a watchlist is just a list of
    tickers someone is watching (no shares, no cost basis, no P&L), while
    a Portfolio represents real positions with real gain/loss.

    Attributes:
        name: Display name for this portfolio (e.g. "Retirement",
            "Trading Account").
        holdings: The actual positions held. Defaults to empty so a new
            Portfolio can be created before any holdings are added.
    """

    name: str
    holdings: list[Holding] = Field(default_factory=list)
