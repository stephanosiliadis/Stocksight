# Import third party packages.
import pandas as pd
import plotly.graph_objects as go

# Import local packages.
from src.visualization.chart_theme import ChartTheme


class IndicatorPlots:
    """
    Builds Plotly traces for individual technical indicator panels.

    This class only turns indicator columns already present on a DataFrame
    (as produced by IndicatorService) into ready-to-place Plotly traces. It
    has no knowledge of subplot rows/layout -- that is TechnicalChart's job,
    which places these traces onto the panels it creates.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        theme: ChartTheme | None = None,
    ) -> None:
        """
        Args:
            data: OHLCV data with calculated indicator columns.
            theme: Color palette. Defaults to a new ChartTheme().
        """
        self._data = data
        self._theme = theme or ChartTheme()

    def build_rsi_traces(self) -> list[go.Scatter]:
        """
        Build the RSI line trace.

        Returns:
            A single-item list with the RSI trace, or [] if RSI is missing.
        """
        if "RSI" not in self._data.columns:
            return []

        return [
            go.Scatter(
                x=self._data.index,
                y=self._data["RSI"],
                name="RSI",
                line=dict(color=self._theme.blue, width=1.2),
            )
        ]

    def build_stochastic_traces(self) -> list[go.Scatter]:
        """
        Build the Stochastic %K and %D line traces.

        Returns:
            List of %K/%D traces, or [] if either column is missing.
        """
        required = {"Stoch_K", "Stoch_D"}
        if not required.issubset(self._data.columns):
            return []

        return [
            go.Scatter(
                x=self._data.index,
                y=self._data["Stoch_K"],
                name="%K",
                line=dict(color=self._theme.orange, dash="dash", width=1.0),
            ),
            go.Scatter(
                x=self._data.index,
                y=self._data["Stoch_D"],
                name="%D",
                line=dict(color=self._theme.tomato, dash="dot", width=1.0),
            ),
        ]

    def build_macd_traces(self) -> list[go.Scatter | go.Bar]:
        """
        Build the MACD line, signal line, and histogram traces.

        Returns:
            List of MACD traces, or [] if any required column is missing.
        """
        required = {"MACD", "MACD_Signal", "MACD_Histogram"}
        if not required.issubset(self._data.columns):
            return []

        histogram = self._data["MACD_Histogram"].fillna(0)
        histogram_colors = [
            self._theme.bullish if value >= 0 else self._theme.bearish
            for value in histogram
        ]

        return [
            go.Scatter(
                x=self._data.index,
                y=self._data["MACD"],
                name="MACD",
                line=dict(color=self._theme.blue, width=1.2),
            ),
            go.Scatter(
                x=self._data.index,
                y=self._data["MACD_Signal"],
                name="Signal",
                line=dict(color=self._theme.orange, width=1.0),
            ),
            go.Bar(
                x=self._data.index,
                y=histogram,
                name="Histogram",
                marker_color=histogram_colors,
                opacity=0.6,
            ),
        ]

    def build_atr_traces(self) -> list[go.Scatter]:
        """
        Build the ATR line trace.

        Returns:
            A single-item list with the ATR trace, or [] if ATR is missing.
        """
        if "ATR" not in self._data.columns:
            return []

        return [
            go.Scatter(
                x=self._data.index,
                y=self._data["ATR"],
                name="ATR",
                line=dict(color=self._theme.gold, width=1.2),
            )
        ]

    def build_volume_traces(self) -> list[go.Bar]:
        """
        Build the Volume bar trace, colored by candle direction.

        Returns:
            A single-item list with the Volume trace, or [] if required
            columns are missing.
        """
        required = {"Volume", "Close", "Open"}
        if not required.issubset(self._data.columns):
            return []

        colors = [
            self._theme.bullish if close >= open_ else self._theme.bearish
            for close, open_ in zip(self._data["Close"], self._data["Open"])
        ]

        return [
            go.Bar(
                x=self._data.index,
                y=self._data["Volume"],
                name="Volume",
                marker_color=colors,
                opacity=0.8,
            )
        ]
