# Import standard library packages.
import json
from datetime import date
from pathlib import Path

# Import third party packages.
import pandas as pd
import streamlit as st

# Import local packages.
from src.components.date_selector import render_date_selector
from src.components.financials_panel import render_financials_panel
from src.components.indicator_selector import render_indicator_selector
from src.components.metrics_cards import render_metrics_cards
from src.components.ticker_input import render_ticker_input
from src.models.analysis_request import AnalysisRequest
from src.models.financial_statements import FinancialStatements
from src.models.statistics import Statistics
from src.services.analysis_service import AnalysisService
from src.utils.validators import ValidationError
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


def _statistics_to_metrics(stats: Statistics) -> dict[str, str]:
    """
    Flatten a Statistics model into the dict shape render_metrics_cards
    expects.
    """
    return {
        "Current Close": f"${stats.current_close:,.2f}",
        "Period High": f"${stats.period_high:,.2f}",
        "High Date": stats.period_high_date.isoformat(),
        "Period Low": f"${stats.period_low:,.2f}",
        "Low Date": stats.period_low_date.isoformat(),
        "% From High": f"{stats.pct_from_high:.2f}%",
        "% From Low": f"{stats.pct_from_low:.2f}%",
    }


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
        )

    return AnalysisRequest(
        tickers=tickers,
        start_date=None,
        end_date=None,
        period=_FREQUENCY_TO_PERIOD.get(frequency, "1y"),
        indicators=indicators,
        include_statements=True,
    )


def show() -> None:
    """
    Render the Stock Analysis page.
    """
    st.title("Stock Analysis")

    # Hydrate the working set from disk on first visit so the user does
    # not lose their tickers when navigating between pages.
    if "selected_tickers" not in st.session_state:
        st.session_state.selected_tickers = _load_cached_tickers()

    tickers = render_ticker_input()
    _save_cached_tickers(tickers)

    if not tickers:
        st.info("Add a ticker above to begin analysis.")
        return

    chart_column, control_column = st.columns([3, 1])

    with control_column:
        indicators = render_indicator_selector()
        period_info = render_date_selector()
        run_analysis = st.button(
            "Analyze",
            type="primary",
            use_container_width=True,
        )

    frequency = period_info["frequency"]
    start_date = period_info.get("start")
    end_date = period_info.get("end")

    # Surface input problems in the control column so the user sees them
    # next to the controls they need to fix.
    validation_error = None
    if not indicators:
        validation_error = "Select at least one indicator."
    elif frequency == "Custom" and (start_date is None or end_date is None):
        validation_error = "Pick a start and an end date for the custom period."

    if validation_error:
        with control_column:
            st.warning(validation_error)
        with chart_column:
            st.info("Adjust the controls on the right to run an analysis.")
        return

    # Run the analysis on demand. Results are cached in session state so
    # re-renders caused by unrelated widget changes do not re-fetch data.
    if run_analysis:
        with st.spinner("Running analysis..."):
            try:
                request = _build_request(
                    tickers=tickers,
                    indicators=indicators,
                    frequency=frequency,
                    start_date=start_date,
                    end_date=end_date,
                )
                service = AnalysisService()
                results = service.analyze(request)
            except ValidationError as exc:
                with control_column:
                    st.error(f"Invalid input: {exc}")
                with chart_column:
                    st.info("Fix the inputs and try again.")
                return
            except Exception as exc:  # noqa: BLE001 - surfaced to the UI
                with control_column:
                    st.error(f"Analysis failed: {exc}")
                with chart_column:
                    st.info("Try again or pick different tickers.")
                return

        st.session_state.analysis_results = results
        st.session_state.analysis_failures = dict(service.failures)

    results = st.session_state.get("analysis_results") or []
    failures: dict[str, str] = st.session_state.get("analysis_failures") or {}

    with chart_column:
        if not results:
            st.info("Click Analyze to generate charts.")
        else:
            for result in results:
                st.subheader(f"{result.ticker} - Technical Chart")
                st.plotly_chart(
                    TechnicalChart(result).build(),
                    use_container_width=True,
                    key=f"chart_{result.ticker}",
                )

    if not results:
        return

    if failures:
        st.warning("Could not analyze: " + ", ".join(sorted(failures)))

    # Financial statements table and statistics live below the chart and
    # control columns, one block per ticker, matching the per-ticker
    # layout of the PDF report.
    for result in results:
        st.divider()
        st.header(result.ticker)

        render_financials_panel(_statements_to_dataframes(result.financial_statements))

        st.subheader("Statistics")
        render_metrics_cards(_statistics_to_metrics(result.statistics))
