# Import standard library packages.
from datetime import date

# Import third party packages.
import plotly.graph_objects as go
import streamlit as st
from dateutil.relativedelta import relativedelta

# Import local packages.
from src.services.comparison_service import ComparisonService
from src.services.correlation_service import CorrelationService
from src.services.data_service import DataService
from src.services.relative_strength_service import RelativeStrengthService

# Matches RelativeStrengthService's own default benchmark, so this page
# compares against the same thing every other page does.
_BENCHMARK_TICKER = "SPY"

_PERIOD_OPTIONS = {
    "3 Months": "3m",
    "6 Months": "6m",
    "1 Year": "1y",
    "2 Years": "2y",
}

_PERIOD_TO_RELATIVEDELTA = {
    "3m": relativedelta(months=3),
    "6m": relativedelta(months=6),
    "1y": relativedelta(years=1),
    "2y": relativedelta(years=2),
}


def _parse_tickers(raw_input: str) -> list[str]:
    """Parse a comma-separated ticker string into a clean, deduped list."""
    seen = set()
    tickers = []
    for piece in raw_input.split(","):
        ticker = piece.strip().upper()
        if ticker and ticker not in seen:
            seen.add(ticker)
            tickers.append(ticker)
    return tickers


def _resolve_date_range(period: str) -> tuple[date, date]:
    """Translate a period key (e.g. '6m') into (start_date, end_date)."""
    end_date = date.today()
    start_date = end_date - _PERIOD_TO_RELATIVEDELTA.get(
        period, relativedelta(months=6)
    )
    return start_date, end_date


def _fetch_all_price_data(tickers: list[str], period: str):
    """Fetch OHLCV data for every ticker plus the benchmark."""
    start_date, end_date = _resolve_date_range(period)
    data_service = DataService()

    price_data = {}
    for ticker in tickers:
        data = data_service.serve_stock_data(
            ticker, start_date.isoformat(), end_date.isoformat()
        )
        if data is not None and not data.empty:
            price_data[ticker] = data

    benchmark_data = data_service.serve_stock_data(
        _BENCHMARK_TICKER, start_date.isoformat(), end_date.isoformat()
    )

    return price_data, benchmark_data


def _render_relative_strength_table(price_data: dict, benchmark_data) -> None:
    """Render each ticker's RelativeStrength vs. the benchmark as a table."""
    if benchmark_data is None or benchmark_data.empty:
        st.info(f"Could not fetch {_BENCHMARK_TICKER} data for comparison.")
        return

    service = RelativeStrengthService()
    rows = []
    for ticker, data in price_data.items():
        relative = service.serve_relative_strength(data, benchmark_data)
        rows.append(
            {
                "Ticker": ticker,
                "Ticker Return": f"{relative.ticker_return_pct:+.2f}%",
                f"{_BENCHMARK_TICKER} Return": f"{relative.benchmark_return_pct:+.2f}%",
                "Relative": f"{relative.relative_pct:+.2f}%",
                "Outperforming": "✅" if relative.outperforming else "❌",
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_correlation_heatmap(price_data: dict) -> None:
    """Render the pairwise return-correlation heatmap."""
    correlation_matrix = CorrelationService().serve_correlation_matrix(price_data)

    if correlation_matrix.empty:
        st.info("Need at least two tickers with overlapping data for correlation.")
        return

    heatmap = go.Figure(
        data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns.tolist(),
            y=correlation_matrix.index.tolist(),
            zmin=-1,
            zmax=1,
            colorscale="RdBu",
            reversescale=True,
            text=correlation_matrix.round(2).values,
            texttemplate="%{text}",
        )
    )
    heatmap.update_layout(
        title="Daily Return Correlation",
        height=420,
        margin=dict(t=50, b=30, l=30, r=30),
    )
    st.plotly_chart(heatmap, use_container_width=True, key="comparison_correlation")


def _run_comparison(tickers: list[str], period: str) -> None:
    """Fetch data and stash it in session state for rendering."""
    with st.spinner("Fetching data..."):
        price_data, benchmark_data = _fetch_all_price_data(tickers, period)

    st.session_state.comparison_price_data = price_data
    st.session_state.comparison_benchmark_data = benchmark_data
    st.session_state.comparison_tickers_run = tickers


def show() -> None:
    """
    Render the Comparison page.

    Every calculation here is delegated to an existing service:
    ComparisonService for the normalized price chart, RelativeStrengthService
    for the per-ticker benchmark table, and CorrelationService for the
    heatmap. This page only fetches raw price data (via DataService) and
    lays the results out -- no new comparison math lives here.
    """
    st.title("🔍 Comparison")
    st.caption(
        "Compare normalized performance, relative strength vs. a benchmark, "
        "and return correlation across multiple tickers."
    )

    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        raw_input = st.text_input(
            "Tickers (comma-separated)",
            placeholder="AAPL, MSFT, GOOGL",
        )
    with col2:
        period_label = st.selectbox("Period", options=list(_PERIOD_OPTIONS.keys()))

    tickers = _parse_tickers(raw_input)

    if len(tickers) < 2:
        st.info("Enter at least two tickers to compare.")
        return

    if st.button("Compare", type="primary"):
        _run_comparison(tickers, _PERIOD_OPTIONS[period_label])

    price_data = st.session_state.get("comparison_price_data")
    benchmark_data = st.session_state.get("comparison_benchmark_data")
    tickers_run = st.session_state.get("comparison_tickers_run")

    if tickers_run != tickers:
        return

    if not price_data:
        st.error(
            "Could not fetch data for any of the given tickers. "
            "Check the symbols and try again."
        )
        return

    st.divider()
    st.subheader("📈 Normalized Performance")
    chart = ComparisonService().serve_comparison(price_data, tickers)
    if chart is not None:
        st.plotly_chart(chart, use_container_width=True, key="comparison_normalized")
    else:
        st.error("Could not generate comparison chart.")

    st.divider()
    st.subheader(f"💪 Relative Strength vs. {_BENCHMARK_TICKER}")
    _render_relative_strength_table(price_data, benchmark_data)

    st.divider()
    st.subheader("🔗 Return Correlation")
    _render_correlation_heatmap(price_data)
