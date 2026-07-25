from __future__ import annotations

import pandas as pd
import yfinance as yf

from src.models.analyst_rating import AnalystRating


class AnalystService:
    """
    Provides functionality for retrieving aggregated analyst sentiment.

    Analyst coverage is inconsistently available across tickers in
    yfinance -- smaller/less-covered names frequently have no
    recommendation breakdown, no price targets, or neither. Every code
    path here degrades to None rather than raising.
    """

    def serve_ratings(self, ticker: str) -> AnalystRating | None:
        """
        Fetch and summarize analyst ratings for a stock ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            AnalystRating summarizing the recommendation consensus and
            price targets, or None if neither is available (including on
            any fetch failure).
        """
        try:
            yf_ticker = yf.Ticker(ticker)
            recommendations = yf_ticker.recommendations
            price_targets = yf_ticker.analyst_price_targets
        except Exception:
            return None

        has_recommendations = (
            isinstance(recommendations, pd.DataFrame) and not recommendations.empty
        )
        has_price_targets = bool(price_targets)

        if not has_recommendations and not has_price_targets:
            return None

        try:
            consensus, num_analysts = self._summarize_recommendations(
                recommendations if has_recommendations else None
            )

            return AnalystRating(
                consensus=consensus,
                num_analysts=num_analysts,
                price_target_mean=self._safe_float(
                    price_targets.get("mean") if has_price_targets else None
                ),
                price_target_high=self._safe_float(
                    price_targets.get("high") if has_price_targets else None
                ),
                price_target_low=self._safe_float(
                    price_targets.get("low") if has_price_targets else None
                ),
            )
        except Exception:
            return None

    def _summarize_recommendations(
        self,
        recommendations: pd.DataFrame | None,
    ) -> tuple[str, int]:
        """
        Derive a majority-vote consensus label and analyst count from the
        recommendations DataFrame's most recent period row.

        Returns:
            ("No Rating", 0) if there's nothing to summarize.
        """
        if recommendations is None or recommendations.empty:
            return "No Rating", 0

        # yfinance's recommendations DataFrame is ordered with the current
        # month's period first (e.g. period "0m").
        latest = recommendations.iloc[0]

        counts = {
            "Strong Buy": self._safe_int(latest.get("strongBuy")),
            "Buy": self._safe_int(latest.get("buy")),
            "Hold": self._safe_int(latest.get("hold")),
            "Sell": self._safe_int(latest.get("sell")),
            "Strong Sell": self._safe_int(latest.get("strongSell")),
        }

        total = sum(counts.values())
        if total == 0:
            return "No Rating", 0

        consensus = max(counts, key=counts.get)
        return consensus, total

    @staticmethod
    def _safe_int(value) -> int:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_float(value) -> float | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
