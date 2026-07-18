from __future__ import annotations

from pydantic import BaseModel


class RelativeStrength(BaseModel):
    ticker_return_pct: float
    benchmark_return_pct: float
    relative_pct: float
    outperforming: bool
    benchmark_ticker: str
