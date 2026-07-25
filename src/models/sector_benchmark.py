from __future__ import annotations

from pydantic import BaseModel


class SectorBenchmark(BaseModel):
    """
    An approximate P/E comparison against a small set of sector peers.

    KNOWN LIMITATION: yfinance has no built-in sector-average P/E
    endpoint. This is NOT a comprehensive sector index or a statistically
    rigorous benchmark -- it's a comparison against a small, manually
    curated list of 2-3 well-known peer tickers per sector (see
    BenchmarkService._SECTOR_PEERS). Treat avg_pe and pe_percentile as
    rough, directional indicators only, not authoritative sector data.

    Attributes:
        sector: The ticker's sector, as reported by yfinance.
        avg_pe: Average trailing P/E across the curated peer list, or
            None if no peer data was available or the sector isn't in
            the curated table.
        ticker_pe: The analyzed ticker's own trailing P/E, or None if
            unavailable.
        pe_percentile: Percentage of curated peers whose P/E is at or
            below the ticker's own P/E (0-100), or None if it can't be
            computed.
    """

    sector: str
    avg_pe: float | None = None
    ticker_pe: float | None = None
    pe_percentile: float | None = None
