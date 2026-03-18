import logging

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)


def fetch_stock_data(
    ticker: str, start_date: str, end_date: str
) -> pd.DataFrame | None:
    """
    Fetch OHLCV stock data for a given ticker and date range from Yahoo Finance.

    Args:
        ticker:     Stock ticker symbol (e.g. 'AAPL').
        start_date: ISO date string for the start of the range.
        end_date:   ISO date string for the end of the range.

    Returns:
        A flat OHLCV DataFrame indexed by date, or None on failure.
    """
    try:
        log.debug(f"Downloading {ticker} from {start_date} to {end_date}")
        stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if stock_data is None or stock_data.empty:
            log.warning(f"No data returned for {ticker} in the given date range.")
            return stock_data

        # Flatten MultiIndex columns (present when fetching a single ticker)
        if isinstance(stock_data.columns, pd.MultiIndex):
            stock_data.columns = stock_data.columns.get_level_values(0)

        log.debug(f"Fetched {len(stock_data)} rows for {ticker}")
        return stock_data

    except Exception as e:
        log.error(f"Error fetching data for {ticker}: {e}")
        return None
