from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class Holding(BaseModel):
    """
    A single real position in a portfolio -- actual shares owned at an
    actual cost, as opposed to a watchlist entry (which is just a ticker
    someone is watching, with no shares or cost basis).

    Attributes:
        ticker: Stock ticker symbol.
        shares: Number of shares held.
        cost_basis: Price paid per share at purchase.
        purchase_date: Date the position was opened.
    """

    ticker: str
    shares: float
    cost_basis: float
    purchase_date: date
