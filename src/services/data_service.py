# Import third party packages.
from pandas import DataFrame

# Import local packages.
from src.utils.data_fetcher import DataFetcher
from src.utils.data_cleaner import DataCleaner


class DataService:
    """
    Provides a high-level interface for retrieving and preparing stock data.

    This service coordinates data retrieval from Yahoo Finance and cleaning
    operations to produce analysis-ready OHLCV market data.
    """

    def __init__(self) -> None:
        """
        Initialize the data service with data fetching and cleaning components.
        """
        self.fetcher = DataFetcher()
        self.cleaner = DataCleaner()

    def serve_stock_data(
        self, ticker: str, start_date: str, end_date: str
    ) -> DataFrame | None:
        """
        Fetch and clean historical stock data for a given ticker.

        Args:
            ticker: Stock ticker symbol to retrieve data for.
            start_date: Start date of the historical data range.
            end_date: End date of the historical data range.

        Returns:
            A cleaned OHLCV DataFrame indexed by date, or None if the data
            could not be retrieved.
        """
        data = self.fetcher.fetch_stock_data(ticker, start_date, end_date)

        if data is not None:
            data = self.cleaner.clean_data(data)

        return data
