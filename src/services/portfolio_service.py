from __future__ import annotations

import pandas as pd

from src.models.fundamentals import Fundamentals
from src.models.holding import Holding
from src.models.portfolio import Portfolio
from src.models.portfolio_analysis import PortfolioAnalysis
from src.services.relative_strength_service import RelativeStrengthService


class PortfolioService:
    """
    Computes allocation, diversification, and benchmark-relative
    performance for a Portfolio of actual holdings.
    """

    def __init__(
        self,
        relative_strength_service: RelativeStrengthService | None = None,
    ) -> None:
        self._relative_strength_service = (
            relative_strength_service or RelativeStrengthService()
        )

    def serve_analysis(
        self,
        portfolio: Portfolio,
        price_data: dict[str, pd.DataFrame],
        fundamentals: dict[str, Fundamentals],
        benchmark_data: pd.DataFrame | None = None,
    ) -> PortfolioAnalysis:
        """
        Compute a full PortfolioAnalysis for the given holdings.

        Args:
            portfolio: The portfolio to analyze.
            price_data: Mapping of ticker -> OHLCV DataFrame (needs a
                "Close" column) covering at least the holding period.
                Tickers missing from this dict fall back to their cost
                basis for valuation (see _current_values).
            fundamentals: Mapping of ticker -> Fundamentals, used only to
                look up each holding's sector for sector_allocation.
                Tickers missing here are grouped under "Unknown".
            benchmark_data: Optional OHLCV DataFrame for the benchmark
                (e.g. SPY) over the same period. When omitted or empty,
                benchmark_return_pct is None.

        Returns:
            PortfolioAnalysis. Degrades to all-zero/empty fields for an
            empty portfolio rather than raising.
        """
        holdings = portfolio.holdings

        if not holdings:
            return PortfolioAnalysis(
                total_value=0.0,
                total_cost=0.0,
                total_return_pct=0.0,
                allocation={},
                sector_allocation={},
                diversification_score=0.0,
                benchmark_return_pct=None,
            )

        holding_values = self._current_values(holdings, price_data)
        total_value = sum(holding_values.values())
        total_cost = sum(holding.shares * holding.cost_basis for holding in holdings)

        total_return_pct = (
            (total_value - total_cost) / total_cost * 100.0 if total_cost > 0 else 0.0
        )

        allocation = self._allocation(holding_values, total_value)
        sector_allocation = self._sector_allocation(
            holding_values, total_value, fundamentals
        )
        diversification_score = self._diversification_score(allocation)
        benchmark_return_pct = self._benchmark_return(
            holdings, price_data, benchmark_data
        )

        return PortfolioAnalysis(
            total_value=float(total_value),
            total_cost=float(total_cost),
            total_return_pct=float(total_return_pct),
            allocation=allocation,
            sector_allocation=sector_allocation,
            diversification_score=float(diversification_score),
            benchmark_return_pct=benchmark_return_pct,
        )

    def _current_values(
        self,
        holdings: list[Holding],
        price_data: dict[str, pd.DataFrame],
    ) -> dict[str, float]:
        """
        Current market value of each holding: shares * most recent Close.

        Holdings with no usable price data fall back to shares *
        cost_basis, so one bad/delisted ticker doesn't drop out of the
        totals entirely -- this is clearly a fallback valuation, not a
        real market price, but keeps the rest of the math from breaking.
        """
        values: dict[str, float] = {}

        for holding in holdings:
            data = price_data.get(holding.ticker)
            if data is not None and not data.empty and "Close" in data.columns:
                close = data["Close"].dropna()
                if not close.empty:
                    values[holding.ticker] = float(holding.shares * close.iloc[-1])
                    continue

            values[holding.ticker] = float(holding.shares * holding.cost_basis)

        return values

    def _allocation(
        self,
        holding_values: dict[str, float],
        total_value: float,
    ) -> dict[str, float]:
        """Each ticker's percentage share of total portfolio value."""
        if total_value <= 0:
            return {ticker: 0.0 for ticker in holding_values}

        return {
            ticker: float(value / total_value * 100.0)
            for ticker, value in holding_values.items()
        }

    def _sector_allocation(
        self,
        holding_values: dict[str, float],
        total_value: float,
        fundamentals: dict[str, Fundamentals],
    ) -> dict[str, float]:
        """Aggregate each ticker's value into its sector's percentage share."""
        if total_value <= 0:
            return {}

        sector_values: dict[str, float] = {}
        for ticker, value in holding_values.items():
            ticker_fundamentals = fundamentals.get(ticker)
            sector = (
                ticker_fundamentals.sector
                if ticker_fundamentals is not None and ticker_fundamentals.sector
                else "Unknown"
            )
            sector_values[sector] = sector_values.get(sector, 0.0) + value

        return {
            sector: float(value / total_value * 100.0)
            for sector, value in sector_values.items()
        }

    def _diversification_score(self, allocation: dict[str, float]) -> float:
        """
        1 - Herfindahl index of allocation weights (as fractions of 1,
        not percentages). A single 100%-weight holding scores 0.0 (fully
        concentrated); an even split across many holdings approaches 1.0.
        """
        if not allocation:
            return 0.0

        weights = [pct / 100.0 for pct in allocation.values()]
        herfindahl_index = sum(weight**2 for weight in weights)

        return float(1.0 - herfindahl_index)

    def _benchmark_return(
        self,
        holdings: list[Holding],
        price_data: dict[str, pd.DataFrame],
        benchmark_data: pd.DataFrame | None,
    ) -> float | None:
        """
        Compare the portfolio's blended value series against the
        benchmark by reusing RelativeStrengthService -- this is a direct
        reuse of Phase 2's return-percentage math, not a second
        independent implementation of it.
        """
        if benchmark_data is None or benchmark_data.empty:
            return None

        portfolio_value_series = self._blended_value_series(holdings, price_data)
        if portfolio_value_series is None or portfolio_value_series.empty:
            return None

        portfolio_frame = pd.DataFrame({"Close": portfolio_value_series})

        relative_strength = self._relative_strength_service.serve_relative_strength(
            portfolio_frame, benchmark_data
        )
        return relative_strength.benchmark_return_pct

    def _blended_value_series(
        self,
        holdings: list[Holding],
        price_data: dict[str, pd.DataFrame],
    ) -> pd.Series | None:
        """
        Build a single portfolio-value-over-time series by summing each
        holding's (shares * Close) across dates every holding shares.
        """
        per_holding_series = []
        for holding in holdings:
            data = price_data.get(holding.ticker)
            if data is None or data.empty or "Close" not in data.columns:
                continue
            per_holding_series.append(data["Close"].astype(float) * holding.shares)

        if not per_holding_series:
            return None

        combined = pd.concat(per_holding_series, axis=1)
        # Only keep dates where every holding has a price, so the blended
        # value isn't distorted by holdings dropping in and out on
        # mismatched trading calendars.
        combined = combined.dropna()

        if combined.empty:
            return None

        return combined.sum(axis=1)
