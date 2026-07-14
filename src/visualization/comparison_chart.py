# Import third party packages.
import pandas as pd
import plotly.graph_objects as go

# Import local packages.
from src.visualization.chart_theme import ChartTheme


class ComparisonChart:
    """
    Builds a normalized relative-performance comparison chart.

    The class only creates Plotly figures and exports them.
    It has no knowledge of Streamlit or filesystem storage.
    """

    def __init__(
        self,
        normalized_data: dict[str, pd.Series],
        theme: ChartTheme | None = None,
    ) -> None:
        """
        Args:
            normalized_data:
                Mapping of ticker symbols to normalized price series.
                Each series should start at 100.
            theme:
                Chart color configuration.
        """
        self._normalized_data = normalized_data
        self._theme = theme or ChartTheme()
        self._figure: go.Figure | None = None

    def build(self) -> go.Figure | None:
        """
        Build the Plotly comparison chart.

        Returns:
            Plotly figure, or None if no valid data exists.
        """
        fig = go.Figure()

        plotted = 0

        for index, (ticker, series) in enumerate(self._normalized_data.items()):
            if series.empty:
                continue

            self._add_series(
                fig,
                ticker,
                series,
                index,
            )

            plotted += 1

        if plotted == 0:
            return None

        self._add_baseline(fig)
        self._configure_layout(fig)

        self._figure = fig

        return fig

    def export_image(
        self,
        format: str = "png",
    ) -> bytes:
        """
        Export the chart as image bytes.

        Args:
            format:
                Image format supported by Plotly/Kaleido.

        Returns:
            Binary image data.

        Raises:
            RuntimeError:
                If build() was not called first.
        """
        if self._figure is None:
            raise RuntimeError("Call build() before exporting.")

        return self._figure.to_image(
            format=format,
        )

    def _add_series(
        self,
        fig: go.Figure,
        ticker: str,
        series: pd.Series,
        index: int,
    ) -> None:
        """
        Add a ticker performance line.
        """
        percentage_change = series.astype(float) - 100

        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=percentage_change,
                name=ticker,
                mode="lines",
                line=dict(
                    color=self._theme.palette[index % len(self._theme.palette)],
                    width=1.8,
                ),
                hovertemplate=(
                    f"{ticker}<br>" "%{x}<br>" "%{y:+.1f}%" "<extra></extra>"
                ),
            )
        )

    def _add_baseline(
        self,
        fig: go.Figure,
    ) -> None:
        """
        Add zero-performance reference line.
        """
        fig.add_hline(
            y=0,
            line_dash="dash",
            opacity=0.7,
        )

    def _configure_layout(
        self,
        fig: go.Figure,
    ) -> None:
        """
        Apply chart layout configuration.
        """
        fig.update_layout(
            title="Relative Price Performance",
            xaxis_title="Date",
            yaxis_title="Performance (%)",
            template="plotly_white",
            height=600,
            hovermode="x unified",
            margin=dict(
                t=60,
                b=30,
                l=50,
                r=30,
            ),
        )

        fig.update_yaxes(
            ticksuffix="%",
        )
