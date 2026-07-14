# Import third party packages.
import pandas as pd
import plotly.graph_objects as go

# Import local packages.
from src.visualization.chart_theme import ChartTheme


class ComparisonChart:
    """
    Builds a normalized relative-performance comparison chart across
    multiple tickers as a single Plotly figure.

    Each ticker's series is expected to already be normalized so its first
    available price equals 100 (see ComparisonService). This class displays
    that as percent change from the start of the period, so a value of 110
    is shown as "+10%".

    This class only builds and returns a go.Figure -- it does not render to
    Streamlit or disk. Callers can pass the figure to st.plotly_chart(fig),
    or call save()/to_html() on this class for exports.
    """

    def __init__(
        self,
        normalized_data: dict[str, pd.Series],
        theme: ChartTheme | None = None,
    ) -> None:
        """
        Args:
            normalized_data: Mapping of ticker symbol to a series indexed to
                a base value of 100 at the first available price.
            theme: Color palette. Defaults to a new ChartTheme().
        """
        self._normalized_data = normalized_data
        self._theme = theme or ChartTheme()
        self._figure: go.Figure | None = None

    def build(self) -> go.Figure | None:
        """
        Assemble the comparison chart.

        Returns:
            The built Plotly figure, or None if no ticker had valid data.
            Also cached on this instance so save()/to_html() can be called
            afterward without rebuilding.
        """
        fig = go.Figure()
        plotted = 0

        for index, (ticker, series) in enumerate(self._normalized_data.items()):
            if series is None or series.empty:
                continue

            self._add_series(fig, ticker, series, index)
            plotted += 1

        if plotted == 0:
            return None

        self._add_baseline(fig)
        self._finalize_layout(fig)

        self._figure = fig
        return fig

    def save(self, output_path: str) -> str:
        """
        Save the built figure to disk.

        Uses write_html() for ".html" paths (no extra dependencies), and
        write_image() otherwise (requires the "kaleido" package).

        Args:
            output_path: Destination file path.

        Returns:
            The output path, for convenience.

        Raises:
            RuntimeError: If build() has not been called yet.
        """
        if self._figure is None:
            raise RuntimeError("Call build() before save().")

        if output_path.endswith(".html"):
            self._figure.write_html(output_path)
        else:
            self._figure.write_image(output_path)

        return output_path

    def to_html(self) -> str:
        """
        Render the built figure as a standalone HTML string.

        Returns:
            HTML markup for the chart.

        Raises:
            RuntimeError: If build() has not been called yet.
        """
        if self._figure is None:
            raise RuntimeError("Call build() before to_html().")

        return self._figure.to_html(include_plotlyjs="cdn")

    def _add_series(
        self,
        fig: go.Figure,
        ticker: str,
        series: pd.Series,
        index: int,
    ) -> None:
        """Add one ticker's line trace, shown as percent change from start."""
        color = self._theme.palette[index % len(self._theme.palette)]
        pct_change = series.astype(float) - 100

        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=pct_change,
                name=ticker,
                mode="lines",
                line=dict(color=color, width=1.8),
                hovertemplate=f"{ticker}<br>%{{x}}<br>%{{y:+.1f}}%<extra></extra>",
            )
        )

    def _add_baseline(self, fig: go.Figure) -> None:
        """Draw the zero-change baseline (the period's starting point)."""
        fig.add_hline(y=0, line_dash="dash", line_color="#555555", opacity=0.7)

    def _finalize_layout(self, fig: go.Figure) -> None:
        """Apply shared figure-level styling (title, axes, template)."""
        fig.update_layout(
            title="Relative Price Performance (Normalized to 100)",
            xaxis_title="Date",
            yaxis_title="Indexed Performance",
            template="plotly_white",
            height=600,
            showlegend=True,
            hovermode="x unified",
            margin=dict(t=60, b=30, l=50, r=30),
        )
        fig.update_yaxes(ticksuffix="%")
