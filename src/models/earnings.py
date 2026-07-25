from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class EarningsEvent(BaseModel):
    """
    A single earnings calendar entry for a ticker.

    Attributes:
        date: The earnings release date.
        is_estimate: Whether this date/figure is a forward-looking
            estimate rather than a reported actual.
        eps_estimate: Consensus EPS estimate for this earnings date, if
            available.
        eps_actual: Reported actual EPS for this earnings date, if
            available. Always None when derived from EarningsService,
            since that service only reuses yfinance's forward-looking
            `.calendar` data, which never contains reported actuals.
    """

    date: date
    is_estimate: bool
    eps_estimate: float | None = None
    eps_actual: float | None = None
