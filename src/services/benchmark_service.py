from __future__ import annotations

from src.models.fundamentals import Fundamentals
from src.models.sector_benchmark import SectorBenchmark
from src.services.fundamentals_service import FundamentalsService

# KNOWN LIMITATION: yfinance has no built-in sector-average P/E endpoint.
# This is a small, manually curated table of 2-3 well-known peer tickers
# per sector, used to approximate a sector comparison -- it is NOT a real
# sector database or index, and sectors not listed here simply have no
# peer comparison available. See SectorBenchmark's docstring for the same
# caveat surfaced to callers of the model itself.
_SECTOR_PEERS: dict[str, list[str]] = {
    "Technology": ["AAPL", "MSFT", "GOOGL"],
    "Healthcare": ["JNJ", "PFE", "UNH"],
    "Financial Services": ["JPM", "BAC", "WFC"],
    "Consumer Cyclical": ["AMZN", "HD", "MCD"],
    "Energy": ["XOM", "CVX", "COP"],
    "Industrials": ["HON", "UNP", "CAT"],
    "Consumer Defensive": ["PG", "KO", "WMT"],
    "Utilities": ["NEE", "DUK", "SO"],
    "Communication Services": ["GOOGL", "META", "DIS"],
    "Basic Materials": ["LIN", "SHW", "FCX"],
    "Real Estate": ["PLD", "AMT", "EQIX"],
}


class BenchmarkService:
    """
    Compares a ticker's P/E ratio against a small set of curated sector
    peers.

    KNOWN LIMITATION: this is an approximation, not a real sector
    database -- see the module-level _SECTOR_PEERS comment and
    SectorBenchmark's docstring for the full caveat. Peer Fundamentals are
    fetched live via FundamentalsService, so this makes 2-3 extra network
    calls per invocation (one per peer).
    """

    def __init__(self, fundamentals_service: FundamentalsService | None = None) -> None:
        self._fundamentals_service = fundamentals_service or FundamentalsService()

    def serve_sector_benchmark(
        self,
        ticker: str,
        fundamentals: Fundamentals | None,
    ) -> SectorBenchmark | None:
        """
        Build a sector P/E comparison for a ticker.

        Args:
            ticker: Stock ticker symbol being analyzed.
            fundamentals: Already-fetched Fundamentals for this ticker
                (reused rather than re-fetched -- this service never
                calls FundamentalsService.serve_fundamentals for the
                ticker itself, only for its peers).

        Returns:
            SectorBenchmark, or None if fundamentals is missing or has no
            sector to compare against.
        """
        if fundamentals is None or not fundamentals.sector:
            return None

        sector = fundamentals.sector
        ticker_pe = fundamentals.pe_ratio
        peers = _SECTOR_PEERS.get(sector, [])

        peer_pe_ratios = self._collect_peer_pe_ratios(ticker, peers)

        if not peer_pe_ratios:
            # Either the sector isn't in our curated table, or none of its
            # peers had a usable P/E -- report what we do know (the
            # ticker's own P/E) rather than fabricating a comparison.
            return SectorBenchmark(
                sector=sector,
                avg_pe=None,
                ticker_pe=ticker_pe,
                pe_percentile=None,
            )

        avg_pe = sum(peer_pe_ratios) / len(peer_pe_ratios)

        return SectorBenchmark(
            sector=sector,
            avg_pe=float(avg_pe),
            ticker_pe=ticker_pe,
            pe_percentile=self._calculate_percentile(ticker_pe, peer_pe_ratios),
        )

    def _collect_peer_pe_ratios(self, ticker: str, peers: list[str]) -> list[float]:
        """Fetch peer Fundamentals on the fly and collect valid P/E ratios."""
        pe_ratios: list[float] = []

        for peer in peers:
            if peer.upper() == ticker.upper():
                continue  # never compare a ticker against itself

            try:
                peer_fundamentals = self._fundamentals_service.serve_fundamentals(peer)
            except Exception:
                continue

            if peer_fundamentals is not None and peer_fundamentals.pe_ratio is not None:
                pe_ratios.append(float(peer_fundamentals.pe_ratio))

        return pe_ratios

    @staticmethod
    def _calculate_percentile(
        ticker_pe: float | None,
        peer_pe_ratios: list[float],
    ) -> float | None:
        """
        Percentage of peers whose P/E is at or below the ticker's own P/E.

        Not a statistically rigorous percentile (the peer set is only
        2-3 tickers) -- a rough directional indicator only.
        """
        if ticker_pe is None or not peer_pe_ratios:
            return None

        at_or_below = sum(1 for pe in peer_pe_ratios if pe <= ticker_pe)
        return float(at_or_below / len(peer_pe_ratios) * 100)
