# Import third party packages.
import pandas as pd

# Import local packages.
from src.models.statistics import Statistics


class StatisticsService:
    """
    Provides functionality for calculating summary statistics from stock data.

    This service computes historical price statistics over a selected analysis
    period, including period highs, lows, current price, and percentage
    distance from extreme values.
    """

    def serve_statistics(self, data: pd.DataFrame) -> Statistics | None:
        """
        Compute historical range statistics for stock market data.

        Args:
            data: OHLCV DataFrame containing historical stock prices.

        Returns:
            Statistics object containing price range metrics, or None if the
            input data is invalid or missing required columns.
        """
        if data is None or data.empty:
            return None

        required_columns = {"High", "Low", "Close"}

        if not required_columns.issubset(data.columns):
            return None

        high_series = data["High"].dropna()
        low_series = data["Low"].dropna()
        close_series = data["Close"].dropna()

        if high_series.empty or low_series.empty or close_series.empty:
            return None

        high_idx = high_series.idxmax()
        low_idx = low_series.idxmin()
        high_date = pd.to_datetime(high_idx).date()
        low_date = pd.to_datetime(low_idx).date()
        period_high = float(high_series.loc[high_idx])
        period_low = float(low_series.loc[low_idx])
        current_close = float(close_series.iloc[-1])
        pct_from_high = (
            ((current_close - period_high) / period_high) * 100 if period_high else 0.0
        )
        pct_from_low = (
            ((current_close - period_low) / period_low) * 100 if period_low else 0.0
        )
        return Statistics(
            period_high=period_high,
            period_high_date=high_date,
            period_low=period_low,
            period_low_date=low_date,
            current_close=current_close,
            pct_from_high=pct_from_high,
            pct_from_low=pct_from_low,
        )
