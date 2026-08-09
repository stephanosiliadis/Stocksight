# Import third party packages.
import pandas as pd


class DataCleaner:
    """
    Provides functionality for cleaning and validating stock market data.

    This class ensures that critical OHLCV (Open, High, Low, Close, Volume)
    columns contain valid numeric values and removes incomplete rows that
    cannot be used for analysis.
    """

    def clean_data(self, data: pd.DataFrame) -> pd.DataFrame | None:
        """
        Clean the stock data by coercing all OHLCV columns to numeric and
        dropping rows that contain NaN in any critical column.

        Returns:
            (pd.DataFrame | None): The cleaned version of the data.
        """
        if not isinstance(data, pd.DataFrame):
            return data

        required_columns = ("Open", "High", "Low", "Close", "Volume")

        # Defense in depth: DataFetcher is expected to hand this a
        # flattened, non-empty frame, but don't assume every required
        # column is actually present as a plain 1-D Series (e.g. a
        # leftover MultiIndex would make data[col] a DataFrame slice, not
        # a Series, and pd.to_numeric would raise on that). Coerce only
        # the columns that are actually there in the expected shape.
        present_columns = [
            col
            for col in required_columns
            if col in data.columns and not isinstance(data[col], pd.DataFrame)
        ]

        if len(present_columns) < len(required_columns):
            # Consistent with every other service in this app (Fundamentals,
            # Earnings, Insider, ...): degrade to "no usable data" instead
            # of raising, since nothing currently wraps this call in a
            # try/except -- raising here would just relocate the crash
            # risk rather than remove it.
            return None

        for col in present_columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

        stock_data = data.dropna(subset=list(required_columns))
        return stock_data
