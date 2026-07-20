# Import standard library packages.
import json
import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

# Import third party packages.
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Import local packages.
from src.components.backtest_panel import render_backtest_panel
from src.components.date_selector import render_date_selector
from src.components.financials_panel import render_financials_panel
from src.components.indicator_selector import render_indicator_selector
from src.components.metrics_cards import render_metrics_cards
from src.components.news_panel import render_news_panel
from src.components.risk_panel import render_risk_inputs, render_trade_plan
from src.components.ticker_input import render_ticker_input
from src.exporters.excel_exporter import ExcelExporter
from src.exporters.pdf_exporter import PDFExporter
from src.models.analysis_request import AnalysisRequest
from src.models.analysis_result import AnalysisResult
from src.models.financial_statements import FinancialStatements
from src.models.statistics import Statistics
from src.services.analysis_service import AnalysisService, DEFAULT_INDICATORS
from src.services.correlation_service import CorrelationService
from src.services.trade_plan_service import TradePlanService
from src.utils.validators import ValidationError
from src.visualization.comparison_chart import ComparisonChart
from src.visualization.technical_chart import TechnicalChart

# Persisted list of tickers the user has been working with, so a page
# refresh or a navigation away does not wipe the working set.
_TICKER_CACHE_FILE = Path("cache/selected_tickers.json")

# Each frequency preset is mapped to a period length that gives a
# reasonable amount of history for that bar size. The AnalysisService
# only accepts a fixed period (e.g. "1y"), so the UI frequency is just
# a friendly label that we translate here.
_FREQUENCY_TO_PERIOD = {
    "Daily": "1y",
    "Weekly": "5y",
    "Monthly": "10y",
}


def _load_cached_tickers() -> list[str]:
    """
    Read the persisted ticker list from disk.

    Returns:
        The cached tickers, or an empty list if the cache is missing
        or unreadable.
    """
    if not _TICKER_CACHE_FILE.exists():
        return []

    try:
        payload = json.loads(_TICKER_CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    tickers = payload.get("tickers", [])
    return [ticker for ticker in tickers if isinstance(ticker, str)]


def _save_cached_tickers(tickers: list[str]) -> None:
    """
    Persist the current ticker list to disk.
    """
    _TICKER_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TICKER_CACHE_FILE.write_text(
        json.dumps({"tickers": list(tickers)}, indent=2),
        encoding="utf-8",
    )


def _statistics_to_metrics(stats: Statistics) -> tuple[dict[str, str], dict[str, str]]:
    """
    Flatten a Statistics model into the (metrics, deltas) shapes
    render_metrics_cards expects. Dates are passed as deltas (small font)
    instead of being appended to the value, since a full date string
    overflows/clips in st.metric's large value font.
    """
    metrics = {
        "Current Close": f"${stats.current_close:,.2f}",
        "Period High": f"${stats.period_high:,.2f}",
        "Period Low": f"${stats.period_low:,.2f}",
        "% From High": f"{stats.pct_from_high:.2f}%",
        "% From Low": f"{stats.pct_from_low:.2f}%",
    }
    deltas = {
        "Period High": stats.period_high_date.isoformat(),
        "Period Low": stats.period_low_date.isoformat(),
    }
    return metrics, deltas


def _statements_to_dataframes(
    statements: FinancialStatements | None,
) -> dict[str, pd.DataFrame] | None:
    """
    Convert a FinancialStatements model into a dict of DataFrames, one
    per available statement, for the financials panel.
    """
    if statements is None:
        return None

    tables: dict[str, pd.DataFrame] = {}

    for label, statement in (
        ("Income Statement", statements.income_statement),
        ("Balance Sheet", statements.balance_sheet),
        ("Cash Flow Statement", statements.cash_flow_statement),
    ):
        if statement is None:
            continue

        tables[label] = pd.DataFrame(
            [row.values for row in statement.rows],
            index=[row.label for row in statement.rows],
            columns=statement.periods,
        )

    return tables or None


def _build_request(
    tickers: list[str],
    indicators: list[str],
    frequency: str,
    start_date: date | None,
    end_date: date | None,
    enable_backtest: bool = False,
    initial_capital: float = 10000.0,
) -> AnalysisRequest:
    """
    Translate the UI selections into an AnalysisRequest.
    """
    if frequency == "Custom":
        return AnalysisRequest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            period=None,
            indicators=indicators,
            include_statements=True,
            backtest=enable_backtest,
            initial_capital=initial_capital,
        )

    return AnalysisRequest(
        tickers=tickers,
        start_date=None,
        end_date=None,
        period=_FREQUENCY_TO_PERIOD.get(frequency, "1y"),
        indicators=indicators,
        include_statements=True,
        backtest=enable_backtest,
        initial_capital=initial_capital,
    )


def _render_sidebar_controls() -> (
    tuple[list[str], list[str], dict, bool, bool, bool, float]
):
    """
    Render every input control in the sidebar, so the main area is left
    free for charts and results.

    Returns:
        Tuple of (tickers, indicators, period_info, show_signals,
        run_analysis, enable_backtest, initial_capital).
    """
    with st.sidebar:
        st.header("Controls")

        tickers = render_ticker_input()
        _save_cached_tickers(tickers)

        st.divider()
        indicators = render_indicator_selector(defaults=DEFAULT_INDICATORS)

        st.divider()
        period_info = render_date_selector()

        st.divider()
        show_signals = st.checkbox(
            "Show buy/sell signals",
            value=True,
            help="Turn off if signal markers are crowding the chart.",
        )

        st.divider()
        enable_backtest = st.checkbox(
            "Run backtest",
            value=False,
            help="Simulate trades based on generated signals.",
        )

        if enable_backtest:
            initial_capital = st.number_input(
                "Initial capital ($)",
                value=10000.0,
                min_value=100.0,
                step=1000.0,
                help="Starting portfolio value for backtest.",
            )
        else:
            initial_capital = 10000.0

        st.divider()
        run_analysis = st.button(
            "Analyze",
            type="primary",
            use_container_width=True,
        )

    return (
        tickers,
        indicators,
        period_info,
        show_signals,
        run_analysis,
        enable_backtest,
        initial_capital,
    )


def _validate_controls(
    indicators: list[str],
    frequency: str,
    start_date: date | None,
    end_date: date | None,
) -> str | None:
    """
    Check the current control selections for obvious problems before
    running an analysis.

    Returns:
        A human-readable error message, or None if everything looks valid.
    """
    if not indicators:
        return "Select at least one indicator."

    if frequency == "Custom" and (start_date is None or end_date is None):
        return "Pick a start and an end date for the custom period."

    return None


def _run_analysis(
    tickers: list[str],
    indicators: list[str],
    frequency: str,
    start_date: date | None,
    end_date: date | None,
    enable_backtest: bool = False,
    initial_capital: float = 10000.0,
) -> bool:
    """
    Build a request, run the analysis, and stash results in session state.

    Returns:
        True if the analysis ran (successfully or not), False if a
        ValidationError/exception was surfaced and nothing was stored.
    """
    with st.spinner("Running analysis..."):
        try:
            request = _build_request(
                tickers=tickers,
                indicators=indicators,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
                enable_backtest=enable_backtest,
                initial_capital=initial_capital,
            )
            service = AnalysisService()
            results = service.analyze(request)
        except ValidationError as exc:
            st.sidebar.error(f"Invalid input: {exc}")
            return False
        except Exception as exc:  # noqa: BLE001 - surfaced to the UI
            st.sidebar.error(f"Analysis failed: {exc}")
            return False

    st.session_state.analysis_results = results
    st.session_state.analysis_failures = dict(service.failures)
    return True


def _render_ticker_result(result: AnalysisResult, show_signals: bool) -> None:
    """
    Render the chart, statistics, financial statements, and backtest results
    for one ticker.
    """
    # Trend badge
    if result.trend is not None:
        trend_label = result.trend.trend.name.title()
        trend_strength = f"{result.trend.strength:.0f}/100"
    else:
        trend_label = "N/A"
        trend_strength = "0/100"

    st.metric("Trend", trend_label, trend_strength)

    chart = TechnicalChart(
        result,
        show_signals=show_signals,
        support_levels=result.support_levels,
        resistance_levels=result.resistance_levels,
        breakout_events=result.breakout_events,
    ).build()
    st.plotly_chart(
        chart,
        use_container_width=True,
        key=f"chart_{result.ticker}",
    )

    st.subheader("� Market Context")
    regime_label = result.regime.regime.name.title() if result.regime else "N/A"
    regime_conf = f"{result.regime.confidence:.0f}/100" if result.regime else "0/100"
    relative_label = (
        f"{result.relative_strength.relative_pct:.2f}% vs {result.relative_strength.benchmark_ticker}"
        if result.relative_strength
        else "N/A"
    )
    relative_delta = (
        f"{result.relative_strength.ticker_return_pct:.2f}% / {result.relative_strength.benchmark_return_pct:.2f}%"
        if result.relative_strength
        else ""
    )
    poc_label = (
        f"${result.volume_profile.point_of_control:.2f}"
        if result.volume_profile
        else "N/A"
    )
    vah_val = (
        f"${result.volume_profile.value_area_low:.2f} - ${result.volume_profile.value_area_high:.2f}"
        if result.volume_profile
        else "N/A"
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Regime", regime_label, regime_conf)
    col2.metric("Relative Strength", relative_label, relative_delta)
    col3.metric("Point of Control", poc_label, vah_val)

    if result.scored_signals:
        with st.expander("Scored Signals", expanded=True):
            scored_table = [
                {
                    "Date": pd.Timestamp(signal.signal.date).date().isoformat(),
                    "Type": signal.signal.signal_type.name.title(),
                    "Price": f"${signal.signal.price:.2f}",
                    "Confidence": f"{signal.confidence:.0f}%",
                    "Factors": ", ".join(signal.contributing_factors) or "none",
                }
                for signal in result.scored_signals
            ]
            st.table(scored_table)

    st.subheader("�📊 Statistics")
    metrics, deltas = _statistics_to_metrics(result.statistics)
    render_metrics_cards(metrics, deltas)

    statements = _statements_to_dataframes(result.financial_statements)
    if statements:
        st.subheader("📑 Financial Statements")
        render_financials_panel(statements)

    # Display backtest results if available
    if result.backtest_result:
        st.divider()
        backtest_data = {
            "total_return": f"{result.backtest_result.total_return:.2f}%",
            "sharpe_ratio": f"{result.backtest_result.sharpe_ratio:.2f}",
            "max_drawdown": f"{result.backtest_result.max_drawdown:.2f}%",
            "win_rate": f"{result.backtest_result.win_rate:.2f}%",
        }
        render_backtest_panel(backtest_data)

    st.divider()
    with st.expander("🧮 Trade Plan", expanded=False):
        account_size, risk_pct = render_risk_inputs(key_prefix=result.ticker)
        plan = TradePlanService().build_plan(
            result=result,
            account_size=account_size,
            risk_pct=risk_pct,
        )
        render_trade_plan(plan)


def _render_comparison_tab(results: list[AnalysisResult]) -> None:
    """
    Render a comparison chart showing normalized price performance across
    multiple tickers, plus a return-correlation heatmap.
    """
    comparison_data = {}
    for result in results:
        normalized = result.raw_data["Close"] / result.raw_data["Close"].iloc[0] * 100
        comparison_data[result.ticker] = normalized

    comparison_chart = ComparisonChart(normalized_data=comparison_data)
    chart_figure = comparison_chart.build()

    if chart_figure is None:
        st.error("Could not generate comparison chart.")
        return

    st.plotly_chart(
        chart_figure,
        use_container_width=True,
        key="comparison_chart",
    )

    st.subheader("🔗 Return Correlation")
    price_data = {result.ticker: result.raw_data for result in results}
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
        height=400,
        margin=dict(t=50, b=30, l=30, r=30),
    )
    st.plotly_chart(heatmap, use_container_width=True, key="correlation_heatmap")


def _render_results(results: list[AnalysisResult], show_signals: bool) -> None:
    """
    Render one tab per ticker when there are multiple results, or a single
    view when there is only one, keeping the page organized regardless of
    how many tickers were analyzed. For multiple results, the last tab
    displays a comparison chart, and the final tab displays news articles.
    """
    if len(results) == 1:
        _render_ticker_result(results[0], show_signals)
        st.divider()
        render_news_panel(results[0].ticker)
        return

    # Create tabs for each ticker plus a final comparison tab and news tab
    tab_labels = [result.ticker for result in results] + ["Comparison", "News"]
    tabs = st.tabs(tab_labels)

    # Render each ticker's individual tab
    for tab, result in zip(tabs[:-2], results):
        with tab:
            _render_ticker_result(result, show_signals)

    # Render the comparison tab
    with tabs[-2]:
        _render_comparison_tab(results)

    # Render the news tab - show articles for all tickers
    with tabs[-1]:
        for result in results:
            render_news_panel(result.ticker)
            st.divider()


def _build_excel_download(results: list[AnalysisResult]) -> tuple[bytes, str, str]:
    """
    Build the Excel download payload for the current results.

    A single ticker downloads its own .xlsx directly. Multiple tickers are
    bundled into one .zip (one .xlsx per ticker inside), since
    ExcelExporter only writes one workbook per AnalysisResult but the page
    should still offer just one button/one file.

    Returns:
        (file_bytes, file_name, mime_type).
    """
    exporter = ExcelExporter()

    if len(results) == 1:
        result = results[0]
        return (
            exporter.export_excel(result),
            f"{result.ticker}_analysis.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for result in results:
            archive.writestr(
                f"{result.ticker}_analysis.xlsx",
                exporter.export_excel(result),
            )
    buffer.seek(0)
    return buffer.getvalue(), "analysis_export.zip", "application/zip"


def _render_export_buttons(results: list[AnalysisResult]) -> None:
    """
    Render Download PDF / Download Excel buttons for the current results.

    Note: both files are (re)built on every rerun this section renders,
    including reruns triggered by unrelated widgets (e.g. the signals
    toggle). PDF generation renders a chart image per ticker via Kaleido,
    so this can get slow with many tickers -- worth revisiting with an
    explicit "Generate" step if that becomes noticeable.
    """
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        pdf_bytes = PDFExporter(results).export()
        st.download_button(
            "📄 Download PDF",
            data=pdf_bytes,
            file_name="analysis_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with col2:
        excel_bytes, excel_name, excel_mime = _build_excel_download(results)
        st.download_button(
            "📊 Download Excel",
            data=excel_bytes,
            file_name=excel_name,
            mime=excel_mime,
            use_container_width=True,
        )


def show() -> None:
    """
    Render the Stock Analysis page.
    """
    st.title("📈 Stock Analysis")
    st.caption("Technical charts, statistics, and financial statements for any ticker.")

    # Hydrate the working set from disk on first visit so the user does
    # not lose their tickers when navigating between pages.
    if "selected_tickers" not in st.session_state:
        st.session_state.selected_tickers = _load_cached_tickers()

    (
        tickers,
        indicators,
        period_info,
        show_signals,
        run_analysis,
        enable_backtest,
        initial_capital,
    ) = _render_sidebar_controls()

    if not tickers:
        st.info("Add a ticker in the sidebar to begin analysis.")
        return

    frequency = period_info["frequency"]
    start_date = period_info.get("start")
    end_date = period_info.get("end")

    validation_error = _validate_controls(indicators, frequency, start_date, end_date)
    if validation_error:
        st.sidebar.warning(validation_error)
        st.info("Adjust the controls in the sidebar to run an analysis.")
        return

    # Run the analysis on demand. Results are cached in session state so
    # re-renders caused by unrelated widget changes do not re-fetch data.
    if run_analysis:
        if not _run_analysis(
            tickers,
            indicators,
            frequency,
            start_date,
            end_date,
            enable_backtest,
            initial_capital,
        ):
            return

    results = st.session_state.get("analysis_results") or []
    failures: dict[str, str] = st.session_state.get("analysis_failures") or {}

    if not results:
        st.info("Click Analyze in the sidebar to generate charts.")
        return

    if failures:
        st.warning("Could not analyze: " + ", ".join(sorted(failures)))

    _render_results(results, show_signals)
    _render_export_buttons(results)
