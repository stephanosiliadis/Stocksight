# Import third party packages.
import pandas as pd
import yfinance as yf

# Import local packages.
from src.models.fundamentals import Fundamentals


class FundamentalsService:
    """
    Provides functionality for retrieving company fundamental information.

    This service fetches valuation metrics, financial ratios, company
    classification data, and earnings information using Yahoo Finance.
    """

    def serve_fundamentals(
        self,
        ticker: str,
    ) -> Fundamentals | None:
        """
        Fetch fundamental data for a stock ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Fundamentals object containing valuation and company metrics,
            or None if the data could not be retrieved.
        """
        try:
            info = yf.Ticker(ticker).info
            fundamentals = Fundamentals(
                pe_ratio=info.get("trailingPE"),
                market_cap=info.get("marketCap"),
                w52_high=info.get("fiftyTwoWeekHigh"),
                w52_low=info.get("fiftyTwoWeekLow"),
                dividend_yield=info.get("dividendYield"),
                sector=info.get("sector"),
                industry=info.get("industry"),
                beta=info.get("beta"),
                eps=info.get("trailingEps"),
                revenue=info.get("totalRevenue"),
                short_name=info.get("shortName"),
            )
            return fundamentals

        except Exception:
            return None

    def serve_earnings_dates(
        self,
        ticker: str,
    ) -> pd.DataFrame | dict | None:
        """
        Fetch upcoming and recent earnings dates for a stock ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            Earnings calendar data as a DataFrame or dictionary,
            or None if unavailable.
        """
        try:
            calendar = yf.Ticker(ticker).calendar

            if isinstance(calendar, dict) and calendar:
                return calendar

            if isinstance(calendar, pd.DataFrame) and not calendar.empty:
                return calendar

        except Exception:
            return None

        return None
