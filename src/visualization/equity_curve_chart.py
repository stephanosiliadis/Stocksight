# Import third party packages.
import pandas as pd
import plotly.graph_objects as go

# Import local packages.
from src.visualization.chart_theme import ChartTheme


class EquityCurveChart:
    """
    Builds a portfolio equity curve chart with shaded drawdown-from-peak
    periods.

    Same shape as ComparisonChart: build() returns a go.Figure, and
    save()/to_html()/export_image() are optional extras for exporting.
    This class only creates Plotly figures -- it has no knowledge of
    Streamlit or filesystem storage beyond writing the file it's asked to.
    """

    def __init__(
        self,
        equity_curve: pd.DataFrame,
        theme: ChartTheme | None = None,
    ) -> None:
        """
        Args:
            equity_curve: DataFrame with a "Portfolio" column (portfolio
                value over time), indexed by date -- the same shape
                BacktestEngine._create_equity_curve() produces.
            theme: Chart color configuration.
        """
        self._equity_curve = equity_curve
        self._theme = theme or ChartTheme()
        self._figure: go.Figure | None = None

    def build(self) -> go.Figure | None:
        """
        Build the equity curve chart.

        Returns:
            Plotly figure, or None if the equity curve is missing/empty
            or doesn't have a "Portfolio" column.
        """
        if not self._has_portfolio_column():
            return None

        portfolio = self._equity_curve["Portfolio"].astype(float)
        running_peak = portfolio.cummax()

        fig = go.Figure()

        self._add_peak_reference(fig, running_peak)
        self._add_portfolio_line(fig, portfolio)
        self._configure_layout(fig)

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

    def export_image(self, format: str = "png") -> bytes:
        """
        Export the chart as image bytes.

        Args:
            format: Image format supported by Plotly/Kaleido.

        Returns:
            Binary image data.

        Raises:
            RuntimeError: If build() was not called first.
        """
        if self._figure is None:
            raise RuntimeError("Call build() before exporting.")

        return self._figure.to_image(format=format)

    def _has_portfolio_column(self) -> bool:
        """Whether the equity curve has usable data to chart."""
        return (
            self._equity_curve is not None
            and not self._equity_curve.empty
            and "Portfolio" in self._equity_curve.columns
        )

    def _add_peak_reference(self, fig: go.Figure, running_peak: pd.Series) -> None:
        """
        Add the invisible running-peak line used purely as the upper
        boundary for the drawdown fill below. Not shown in the legend or
        on hover, since it isn't a data series a viewer needs to read.
        """
        fig.add_trace(
            go.Scatter(
                x=self._equity_curve.index,
                y=running_peak,
                name="Peak",
                mode="lines",
                line=dict(width=0),
                hoverinfo="skip",
                showlegend=False,
            )
        )

    def _add_portfolio_line(self, fig: go.Figure, portfolio: pd.Series) -> None:
        """
        Add the portfolio value line, filled up to the running-peak trace
        added just before it. Where the portfolio is at a new high, the
        portfolio value equals the running peak, so the fill collapses to
        zero width and nothing is shaded -- only periods below a prior
        peak (drawdowns) end up visibly shaded.
        """
        fig.add_trace(
            go.Scatter(
                x=self._equity_curve.index,
                y=portfolio,
                name="Portfolio Value",
                mode="lines",
                line=dict(color=self._theme.blue, width=2),
                fill="tonexty",
                fillcolor="rgba(239, 83, 80, 0.25)",
                hovertemplate="%{x}<br>$%{y:,.2f}<extra></extra>",
            )
        )

    def _configure_layout(self, fig: go.Figure) -> None:
        """Apply chart layout configuration."""
        fig.update_layout(
            title="Equity Curve",
            xaxis_title="Date",
            yaxis_title="Portfolio Value ($)",
            template="plotly_white",
            height=400,
            hovermode="x unified",
            margin=dict(t=50, b=30, l=50, r=30),
        )
        fig.update_yaxes(tickprefix="$", separatethousands=True)
