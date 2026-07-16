# Import third party packages.
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import local packages.
from src.models.analysis_result import AnalysisResult
from src.models.signal import Signal, SignalType
from src.visualization.chart_theme import ChartTheme
from src.visualization.indicator_plots import IndicatorPlots


class TechnicalChart:
    """
    Builds a multi-panel technical analysis chart as a single Plotly figure.

    Only panels for currently active indicators are created: an optional
    oscillator row (RSI and/or Stochastic) on top, the candlestick panel
    (always present, with Bollinger Bands / EMA overlays, buy/sell markers,
    and support/resistance lines), then optional Volume, MACD, and ATR rows
    below.

    This class only builds and returns a go.Figure -- it does not render to
    Streamlit or disk. Callers can pass the figure to st.plotly_chart(fig),
    or call save()/to_html() on this class for exports.
    """

    def __init__(
        self,
        result: AnalysisResult,
        show_signals: bool = True,
        support_levels: list[float] | None = None,
        resistance_levels: list[float] | None = None,
        show_volume: bool = True,
        theme: ChartTheme | None = None,
    ) -> None:
        """
        Args:
            result: The analysis result to chart. Supplies the indicator
                data, ticker, active indicator list, and signals.
            show_signals: Whether to plot buy/sell markers. Signals can
                crowd the chart and obscure candle values, so callers can
                let the user toggle this off.
            support_levels: Horizontal support levels to draw. Optional.
            resistance_levels: Horizontal resistance levels to draw. Optional.
            show_volume: Whether to include a Volume panel.
            theme: Color palette. Defaults to a new ChartTheme().
        """
        self._data = self._normalize_index(result.indicators)
        self._ticker = result.ticker
        self._indicators = result.active_indicators
        self._signals = result.signals if show_signals else []
        self._support_levels = support_levels or []
        self._resistance_levels = resistance_levels or []
        self._show_volume = show_volume
        self._theme = theme or ChartTheme()
        self._indicator_plots = IndicatorPlots(self._data, self._theme)
        self._figure: go.Figure | None = None

    def _normalize_index(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure the DataFrame has a proper datetime64 DatetimeIndex.

        If the index arrives as dtype "object" holding individual
        Timestamp instances (rather than a vectorized datetime64 index),
        every trace built from it serializes element-by-element instead
        of as a single array. That's harmless for the interactive
        st.plotly_chart view, but breaks Kaleido's orjson-based PNG
        export (used for PDF/Excel charts) with
        "Type is not JSON serializable: Timestamp". Coercing here once
        means every trace built downstream is safe regardless of what
        dtype the index arrived as.
        """
        data = data.copy()
        data.index = pd.DatetimeIndex(data.index)
        return data

    def build(self) -> go.Figure:
        """
        Assemble the full multi-panel chart.

        Returns:
            The built Plotly figure. Also cached on this instance so
            save()/to_html() can be called afterward without rebuilding.
        """
        layout = self._plan_layout()
        fig = make_subplots(
            rows=len(layout),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[ratio for _, ratio in layout],
        )
        rows = {name: index + 1 for index, (name, _) in enumerate(layout)}

        self._add_candlestick(fig, rows["candle"])
        self._add_overlays(fig, rows["candle"])
        self._add_signal_markers(fig, rows["candle"])
        self._add_support_resistance(fig, rows["candle"])

        if "oscillator" in rows:
            self._add_oscillator_panel(fig, rows["oscillator"])

        if "volume" in rows:
            self._add_traces(
                fig, rows["volume"], self._indicator_plots.build_volume_traces()
            )

        if "macd" in rows:
            self._add_macd_panel(fig, rows["macd"])

        if "atr" in rows:
            self._add_traces(fig, rows["atr"], self._indicator_plots.build_atr_traces())

        self._finalize_layout(fig, len(layout))
        fig.update_xaxes(rangeslider_visible=False, row=rows["candle"], col=1)

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

    def _plan_layout(self) -> list[tuple[str, float]]:
        """
        Determine which panels are active and their relative heights, in
        top-to-bottom row order.

        Returns:
            List of (panel_name, height_ratio) tuples.
        """
        layout: list[tuple[str, float]] = []

        if self._has_rsi() or self._has_stochastic():
            layout.append(("oscillator", self._theme.oscillator_ratio))

        layout.append(("candle", self._theme.candle_ratio))

        if self._show_volume and "Volume" in self._data.columns:
            layout.append(("volume", self._theme.secondary_ratio))

        if "macd" in self._indicators and "MACD" in self._data.columns:
            layout.append(("macd", self._theme.secondary_ratio))

        if "atr" in self._indicators and "ATR" in self._data.columns:
            layout.append(("atr", self._theme.secondary_ratio))

        return layout

    def _has_rsi(self) -> bool:
        """Whether RSI is active and available."""
        return "rsi" in self._indicators and "RSI" in self._data.columns

    def _has_stochastic(self) -> bool:
        """Whether Stochastic is active and available."""
        return "stochastic" in self._indicators and {"Stoch_K", "Stoch_D"}.issubset(
            self._data.columns
        )

    def _add_candlestick(self, fig: go.Figure, row: int) -> None:
        """Add the main OHLC candlestick trace."""
        fig.add_trace(
            go.Candlestick(
                x=self._data.index,
                open=self._data["Open"],
                high=self._data["High"],
                low=self._data["Low"],
                close=self._data["Close"],
                name=self._ticker,
                increasing_line_color=self._theme.bullish,
                decreasing_line_color=self._theme.bearish,
            ),
            row=row,
            col=1,
        )

    def _add_overlays(self, fig: go.Figure, row: int) -> None:
        """Add Bollinger Bands and EMA overlays onto the candlestick panel."""
        if "bollinger" in self._indicators and "Bollinger_Upper" in self._data.columns:
            self._add_line(
                fig, row, "Bollinger_Upper", "BB Upper", self._theme.purple, dash="dash"
            )
            self._add_line(
                fig, row, "Bollinger_Lower", "BB Lower", self._theme.purple, dash="dash"
            )

        ema_specs = [
            ("EMA20", "ema20", "EMA 20", self._theme.cyan),
            ("EMA50", "ema50", "EMA 50", self._theme.lime),
            ("EMA200", "ema200", "EMA 200", self._theme.tomato),
        ]
        for column, key, label, color in ema_specs:
            if key in self._indicators and column in self._data.columns:
                self._add_line(fig, row, column, label, color)

    def _add_line(
        self,
        fig: go.Figure,
        row: int,
        column: str,
        label: str,
        color: str,
        dash: str | None = None,
    ) -> None:
        """Add a single overlay line trace onto a given panel row."""
        line = dict(color=color, width=1.0)
        if dash:
            line["dash"] = dash

        fig.add_trace(
            go.Scatter(
                x=self._data.index,
                y=self._data[column],
                name=label,
                line=line,
            ),
            row=row,
            col=1,
        )

    def _add_signal_markers(self, fig: go.Figure, row: int) -> None:
        """Add buy/sell signal scatter markers onto the candlestick panel."""
        buys = [s for s in self._signals if s.signal_type is SignalType.BUY]
        sells = [s for s in self._signals if s.signal_type is SignalType.SELL]

        if buys:
            self._add_signal_trace(
                fig, row, buys, "Buy Signal", "triangle-up", self._theme.bullish
            )

        if sells:
            self._add_signal_trace(
                fig, row, sells, "Sell Signal", "triangle-down", self._theme.bearish
            )

    def _add_signal_trace(
        self,
        fig: go.Figure,
        row: int,
        signals: list[Signal],
        label: str,
        symbol: str,
        color: str,
    ) -> None:
        """Add one scatter trace (buy or sell) built from a list of Signals."""
        fig.add_trace(
            go.Scatter(
                x=[pd.Timestamp(s.date).to_pydatetime() for s in signals],
                y=[s.price for s in signals],
                name=label,
                mode="markers",
                marker=dict(
                    symbol=symbol,
                    size=11,
                    color=color,
                    line=dict(width=1, color="white"),
                ),
                text=[s.reason for s in signals],
                hovertemplate="%{text}<br>%{x}<br>$%{y:.2f}<extra></extra>",
            ),
            row=row,
            col=1,
        )

    def _add_support_resistance(self, fig: go.Figure, row: int) -> None:
        """Draw horizontal support and resistance lines on the candlestick panel."""
        for level in self._support_levels:
            fig.add_hline(
                y=level,
                row=row,
                col=1,
                line_dash="dot",
                line_color=self._theme.lime,
                opacity=0.75,
            )

        for level in self._resistance_levels:
            fig.add_hline(
                y=level,
                row=row,
                col=1,
                line_dash="dot",
                line_color=self._theme.tomato,
                opacity=0.75,
            )

    def _add_oscillator_panel(self, fig: go.Figure, row: int) -> None:
        """Add RSI and/or Stochastic traces plus threshold lines to the oscillator panel."""
        has_rsi = self._has_rsi()

        if has_rsi:
            self._add_traces(fig, row, self._indicator_plots.build_rsi_traces())

        if self._has_stochastic():
            self._add_traces(fig, row, self._indicator_plots.build_stochastic_traces())

        oversold, overbought = (30, 70) if has_rsi else (20, 80)
        fig.add_hline(
            y=oversold,
            row=row,
            col=1,
            line_dash="dash",
            line_color=self._theme.lime,
            opacity=0.9,
        )
        fig.add_hline(
            y=overbought,
            row=row,
            col=1,
            line_dash="dash",
            line_color=self._theme.tomato,
            opacity=0.9,
        )
        fig.update_yaxes(range=[0, 100], row=row, col=1)

    def _add_macd_panel(self, fig: go.Figure, row: int) -> None:
        """Add MACD traces and the zero line to the MACD panel."""
        self._add_traces(fig, row, self._indicator_plots.build_macd_traces())
        fig.add_hline(y=0, row=row, col=1, line_color="gray", opacity=0.5)

    def _add_traces(self, fig: go.Figure, row: int, traces: list) -> None:
        """Add a batch of pre-built traces onto a given panel row."""
        for trace in traces:
            fig.add_trace(trace, row=row, col=1)

    def _finalize_layout(self, fig: go.Figure, panel_count: int) -> None:
        """Apply shared figure-level styling (title, height, template)."""
        fig.update_layout(
            title=f"{self._ticker} — Technical Analysis",
            template="plotly_white",
            height=max(650, 300 + panel_count * 200),
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            hovermode="x unified",
            margin=dict(t=70, b=30, l=50, r=30),
        )
