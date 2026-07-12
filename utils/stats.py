import logging

import pandas as pd

log = logging.getLogger(__name__)


def compute_range_stats(data: pd.DataFrame) -> dict:
    """
    Compute historical high/low statistics for the given (already trimmed to
    the user's selected date range) OHLCV DataFrame.

    Returns:
        dict with period_high, period_high_date, period_low, period_low_date,
        current_close, pct_from_high, pct_from_low. Empty dict if data is
        invalid or missing required columns.
    """
    if data is None or data.empty:
        return {}
    if (
        "High" not in data.columns
        or "Low" not in data.columns
        or "Close" not in data.columns
    ):
        return {}

    high_series = data["High"].dropna()
    low_series = data["Low"].dropna()
    close_series = data["Close"].dropna()

    if high_series.empty or low_series.empty or close_series.empty:
        return {}

    high_idx = high_series.idxmax()
    low_idx = low_series.idxmin()
    period_high = float(high_series.loc[high_idx])
    period_low = float(low_series.loc[low_idx])
    current_close = float(close_series.iloc[-1])

    pct_from_high = (
        ((current_close - period_high) / period_high) * 100 if period_high else 0.0
    )
    pct_from_low = (
        ((current_close - period_low) / period_low) * 100 if period_low else 0.0
    )

    stats = {
        "period_high": period_high,
        "period_high_date": high_idx,
        "period_low": period_low,
        "period_low_date": low_idx,
        "current_close": current_close,
        "pct_from_high": pct_from_high,
        "pct_from_low": pct_from_low,
    }

    log.debug(f"Range stats: {stats}")
    return stats
