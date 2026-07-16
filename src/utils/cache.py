# Import standard library packages.
from dataclasses import dataclass, field
from datetime import date

# Import third party packages.
import pandas as pd


@dataclass
class CacheEntry:
    """
    Stores cached analysis data for a ticker over a specific date range.

    Attributes:
        ticker: Stock ticker symbol.
        start_date: Start date of the cached data.
        end_date: End date of the cached data.
        raw_data: OHLCV data for the date range.
        indicators: Calculated indicator data for the date range.
        signals: Generated trading signals for the date range.
    """

    ticker: str
    start_date: date
    end_date: date
    raw_data: pd.DataFrame
    indicators: pd.DataFrame
    signals: list  # List of Signal objects


class AnalysisCache:
    """
    Manages cached analysis data, supporting incremental fetching.

    When a request overlaps with cached data, returns the cached portion
    and indicates what new data needs to be fetched to complete the request.
    """

    def __init__(self) -> None:
        """Initialize the cache as empty."""
        self._cache: dict[str, list[CacheEntry]] = {}

    def get_cache_status(
        self,
        ticker: str,
        requested_start: date,
        requested_end: date,
    ) -> tuple[CacheEntry | None, date | None, date | None]:
        """
        Check cache for overlap with the requested date range.

        Args:
            ticker: Stock ticker symbol.
            requested_start: Requested start date.
            requested_end: Requested end date.

        Returns:
            A tuple of (cached_entry, fetch_start, fetch_end) where:
            - cached_entry: The overlapping cached data, or None if no overlap.
            - fetch_start: The start date for new data to fetch, or None if
              nothing needs fetching.
            - fetch_end: The end date for new data to fetch, or None if
              nothing needs fetching.

            If the entire requested range is cached, fetch_start and fetch_end
            are None. If nothing is cached, cached_entry is None and fetch
            dates span the full requested range.
        """
        if ticker not in self._cache or not self._cache[ticker]:
            # No cache for this ticker; fetch the full range
            return None, requested_start, requested_end

        # Find the entry that best overlaps with the request
        entries = self._cache[ticker]
        overlapping = [
            e
            for e in entries
            if e.start_date <= requested_end and e.end_date >= requested_start
        ]

        if not overlapping:
            # No overlap; fetch the full range
            return None, requested_start, requested_end

        # Use the most recent overlapping entry
        cached_entry = max(overlapping, key=lambda e: e.end_date)

        # Determine what new data is needed
        fetch_start = None
        fetch_end = None

        if requested_start < cached_entry.start_date:
            # Need data before the cached range
            fetch_start = requested_start
            fetch_end = cached_entry.start_date

        if requested_end > cached_entry.end_date:
            # Need data after the cached range
            if fetch_start is None:
                fetch_start = cached_entry.end_date
            fetch_end = requested_end

        return cached_entry, fetch_start, fetch_end

    def store_cache(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
        raw_data: pd.DataFrame,
        indicators: pd.DataFrame,
        signals: list,
    ) -> None:
        """
        Store analysis data in the cache.

        Args:
            ticker: Stock ticker symbol.
            start_date: Start date of the data.
            end_date: End date of the data.
            raw_data: OHLCV market data.
            indicators: Calculated indicator columns.
            signals: List of generated signals.
        """
        if ticker not in self._cache:
            self._cache[ticker] = []

        entry = CacheEntry(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            raw_data=raw_data.copy(),
            indicators=indicators.copy(),
            signals=signals.copy(),
        )
        self._cache[ticker].append(entry)

    def merge_data(
        self,
        cached_entry: CacheEntry | None,
        new_raw_data: pd.DataFrame | None,
        new_indicators: pd.DataFrame | None,
        new_signals: list | None,
        requested_start: date,
        requested_end: date,
    ) -> tuple[pd.DataFrame, pd.DataFrame, list]:
        """
        Merge cached data with newly fetched data to cover the full range.

        Args:
            cached_entry: The cached entry (if any).
            new_raw_data: Newly fetched raw OHLCV data (if any).
            new_indicators: Newly fetched indicator data (if any).
            new_signals: Newly fetched signals (if any).
            requested_start: The start of the requested range.
            requested_end: The end of the requested range.

        Returns:
            A tuple of (merged_raw_data, merged_indicators, merged_signals).
        """
        raw_dfs = []
        indicator_dfs = []
        all_signals = []

        # Add cached data if it exists
        if cached_entry is not None:
            raw_dfs.append(cached_entry.raw_data)
            indicator_dfs.append(cached_entry.indicators)
            all_signals.extend(cached_entry.signals)

        # Add new data if it exists
        if new_raw_data is not None and not new_raw_data.empty:
            raw_dfs.append(new_raw_data)
        if new_indicators is not None and not new_indicators.empty:
            indicator_dfs.append(new_indicators)
        if new_signals:
            all_signals.extend(new_signals)

        # Merge DataFrames
        if raw_dfs:
            merged_raw = pd.concat(raw_dfs).drop_duplicates().sort_index()
        else:
            merged_raw = pd.DataFrame()

        if indicator_dfs:
            merged_indicators = pd.concat(indicator_dfs).drop_duplicates().sort_index()
        else:
            merged_indicators = pd.DataFrame()

        # Remove duplicate signals by date and type
        unique_signals = {}
        for sig in all_signals:
            key = (sig.date, sig.signal_type)
            if key not in unique_signals:
                unique_signals[key] = sig

        return merged_raw, merged_indicators, list(unique_signals.values())
