import logging

import pandas as pd

log = logging.getLogger(__name__)


def clean_data(stock_data: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the stock data by coercing all OHLCV columns to numeric and
    dropping rows that contain NaN in any critical column.
    """
    if not isinstance(stock_data, pd.DataFrame):
        log.error("stock_data is not a pandas DataFrame — returning as-is.")
        return stock_data

    log.debug(f"Cleaning data — input shape: {stock_data.shape}")

    for col in ("Open", "High", "Low", "Close", "Volume"):
        stock_data[col] = pd.to_numeric(stock_data[col], errors="coerce")

    before = len(stock_data)
    stock_data = stock_data.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    dropped = before - len(stock_data)

    if dropped:
        log.debug(f"Dropped {dropped} rows with NaN values.")

    log.debug(f"Cleaned data shape: {stock_data.shape}")
    return stock_data
