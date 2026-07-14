# Import third party packages.
import pandas as pd
import plotly.graph_objects as go

# Import local packages.
from src.visualization.comparison_chart import ComparisonChart


class ComparisonService:
    """
    Provides functionality for comparing historical performance between
    multiple stock tickers.

    This service normalizes closing prices and delegates chart creation to
    the visualization layer.
    """

    def serve_comparison(
        self,
        analyzed_data: dict[str, pd.DataFrame],
        tickers: list[str],
    ) -> go.Figure | None:
        """
        Generate a normalized performance comparison chart.

        Args:
            analyzed_data: Dictionary mapping ticker symbols to historical
                OHLCV DataFrames.
            tickers: List of ticker symbols to compare.

        Returns:
            The comparison chart figure, or None if no valid tickers are
            available. Callers can pass this to st.plotly_chart(fig), or
            call .save()/.to_html() on it for exports.
        """
        normalized_data = {}

        for ticker in tickers:
            data = analyzed_data.get(ticker)

            if data is None or data.empty:
                continue

            if "Close" not in data.columns:
                continue

            close = data["Close"].dropna()

            if close.empty:
                continue

            first_price = close.iloc[0]

            if first_price == 0:
                continue

            normalized_data[ticker] = (close.astype(float) / float(first_price)) * 100

        if not normalized_data:
            return None

        return ComparisonChart(normalized_data).build()
