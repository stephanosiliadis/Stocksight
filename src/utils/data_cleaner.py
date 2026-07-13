# Import third party packages.
import pandas as pd


class DataCleaner:
    """
    Provides functionality for cleaning and validating stock market data.

    This class ensures that critical OHLCV (Open, High, Low, Close, Volume)
    columns contain valid numeric values and removes incomplete rows that
    cannot be used for analysis.
    """

    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Clean the stock data by coercing all OHLCV columns to numeric and
        dropping rows that contain NaN in any critical column.

        Returns:
            (pd.DataFrame | None): The cleaned version of the data.
        """
        if not isinstance(data, pd.DataFrame):
            return data

        for col in ("Open", "High", "Low", "Close", "Volume"):
            data[col] = pd.to_numeric(data[col], errors="coerce")

        stock_data = data.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
        return stock_data
