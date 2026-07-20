from __future__ import annotations

import pandas as pd


class CorrelationService:
    """
    Computes a Pearson correlation matrix of daily percentage returns
    across multiple tickers.

    This is a page-level feature (used by the Comparison page), not part
    of AnalysisService.analyze() -- it needs multiple tickers' raw_data
    at once, which the Comparison page already assembles for its existing
    normalized-performance chart.
    """

    def serve_correlation_matrix(
        self,
        price_data: dict[str, pd.DataFrame],
    ) -> pd.DataFrame:
        """
        Build a ticker x ticker Pearson correlation matrix of daily % returns.

        Args:
            price_data: Mapping of ticker symbol to an OHLCV DataFrame
                containing at least a "Close" column.

        Returns:
            A symmetric DataFrame indexed and columned by ticker, with
            1.0 on the diagonal. Returns an empty DataFrame if fewer than
            two tickers have usable data.
        """
        returns: dict[str, pd.Series] = {}

        for ticker, data in price_data.items():
            if data is None or data.empty or "Close" not in data.columns:
                continue

            close = data["Close"].dropna()
            if len(close) < 2:
                continue

            pct_returns = close.astype(float).pct_change().dropna()
            if pct_returns.empty:
                continue

            returns[ticker] = pct_returns

        if len(returns) < 2:
            return pd.DataFrame()

        # Align all return series on their shared dates. Tickers with
        # non-overlapping calendars (e.g. different listing histories)
        # will simply produce NaN correlations for those pairs rather
        # than raising.
        combined = pd.DataFrame(returns)

        correlation_matrix = combined.corr(method="pearson")

        return correlation_matrix
