from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class InsiderTransaction(BaseModel):
    """
    A single insider buy/sell transaction for a ticker.

    Attributes:
        insider_name: Name of the reporting insider.
        date: Date the transaction was executed/reported.
        transaction_type: Transaction description as reported (e.g.
            "Sale", "Purchase", "Award" -- exact wording varies by source).
        shares: Number of shares involved in the transaction.
        value: Dollar value of the transaction, if reported.
    """

    insider_name: str
    date: date
    transaction_type: str
    shares: int
    value: float | None = None
