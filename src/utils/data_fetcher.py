# Import third party packages.
import pandas as pd
import yfinance as yf


class DataFetcher:
    """
    Handles retrieval of historical stock market data from Yahoo Finance.

    This class provides methods for fetching OHLCV (Open, High, Low, Close,
    Volume) data for a single ticker symbol within a specified date
    range.
    """

    def fetch_stock_data(
        self, ticker: str, start_date: str, end_date: str
    ) -> pd.DataFrame | None:
        """
        Fetch OHLCV stock data for a given ticker and date range from Yahoo Finance.

        Args:
            ticker: Stock ticker symbol (e.g. "AAPL").
            start_date: Start date of the requested historical period.
            end_date: End date of the requested historical period.

        Returns:
            A DataFrame containing historical OHLCV data indexed by date,
            or None if the data could not be retrieved.
        """
        try:
            stock_data = yf.download(
                ticker, start=start_date, end=end_date, progress=False
            )

            if stock_data is None or stock_data.empty:
                return stock_data

            # Flatten MultiIndex columns (present when fetching a single ticker)
            if isinstance(stock_data.columns, pd.MultiIndex):
                stock_data.columns = stock_data.columns.get_level_values(0)

            return stock_data

        except Exception:
            return None
