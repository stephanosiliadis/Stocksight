import logging
import yfinance as yf

log = logging.getLogger(__name__)


def fetch_fundamentals(ticker: str) -> dict:
    """
    Fetch fundamental data for a ticker using yfinance.

    Returns a flat dict of commonly used valuation and financial metrics.
    Missing fields are returned as None so callers can display 'N/A' safely.
    """
    try:
        info = yf.Ticker(ticker).info
        return {
            "pe_ratio": info.get("trailingPE"),
            "market_cap": info.get("marketCap"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "dividend_yield": info.get("dividendYield"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "beta": info.get("beta"),
            "eps": info.get("trailingEps"),
            "revenue": info.get("totalRevenue"),
            "short_name": info.get("shortName"),
        }
    except Exception as e:
        log.warning(f"Could not fetch fundamentals for {ticker}: {e}")
        return {}


def fetch_earnings_dates(ticker: str):
    """
    Fetch upcoming / recent earnings dates for a ticker.

    Returns the calendar DataFrame from yfinance, or None if unavailable.
    """
    try:
        t = yf.Ticker(ticker)
        import pandas as pd

        calendar = t.calendar
        if isinstance(calendar, dict) and calendar:
            return calendar
        if isinstance(calendar, pd.DataFrame) and not calendar.empty:
            return calendar
    except Exception as e:
        log.warning(f"Could not fetch earnings dates for {ticker}: {e}")
    return None
