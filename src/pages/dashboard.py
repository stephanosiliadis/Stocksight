# Import third party packages.
import pandas as pd
import streamlit as st

# Import local packages.
from src.models.analysis_request import AnalysisRequest
from src.models.analysis_result import AnalysisResult
from src.services.analysis_service import AnalysisService
from src.utils.watchlist_storage import load_watchlist

# Kept deliberately short/minimal for speed -- this page is a scan, not a
# deep-dive. "3m" is enough history for EMA50 (TrendService's own
# requirement) to be meaningful; ema200 needs more history to fully
# populate but TrendService degrades to SIDEWAYS/0 rather than raising
# when it can't compute, per its existing documented behavior. rsi is
# included so SignalService has something to generate scored_signals
# from, since a "most recent scored signal" column would otherwise always
# be empty.
_SCAN_PERIOD = "3m"
_SCAN_INDICATORS = ["ema50", "ema200", "rsi"]


def _run_scan(tickers: list[str]) -> list[AnalysisResult]:
    """
    Run a lightweight analyze() across the watchlist.

    Reuses AnalysisService.analyze() exactly as-is -- no separate calls to
    TrendService/MarketRegimeService/SignalScoringService here, since
    analyze() already orchestrates all of that (plus caching and
    per-ticker isolation) for every result it returns. The only thing
    this page controls is which indicators/period to ask for, to keep the
    request cheap: no fundamentals, no statements, no backtest, no
    earnings/analyst/insider data -- all off by default already, but
    listed here so it's clear this scan never fetches them.
    """
    request = AnalysisRequest(
        tickers=tickers,
        period=_SCAN_PERIOD,
        indicators=_SCAN_INDICATORS,
        include_fundamentals=False,
        include_statements=False,
        include_earnings=False,
        include_analyst_ratings=False,
        include_insider_activity=False,
        backtest=False,
    )
    service = AnalysisService()
    results = service.analyze(request)
    st.session_state.dashboard_failures = dict(service.failures)
    return results


def _latest_scored_signal(result: AnalysisResult):
    """Most recent scored signal for a result, or None if it has none."""
    if not result.scored_signals:
        return None
    return max(result.scored_signals, key=lambda scored: scored.signal.date)


def _build_scan_table(results: list[AnalysisResult]) -> pd.DataFrame:
    """
    Flatten scan results into a compact table: one row per ticker, trend,
    regime, and most recent scored signal -- not a full chart per ticker,
    this page is a scan.
    """
    rows = []

    for result in results:
        trend_label = result.trend.trend.name.title() if result.trend else "N/A"
        trend_strength = f"{result.trend.strength:.0f}/100" if result.trend else "-"

        regime_label = result.regime.regime.name.title() if result.regime else "N/A"
        regime_confidence = (
            f"{result.regime.confidence:.0f}/100" if result.regime else "-"
        )

        latest_signal = _latest_scored_signal(result)
        if latest_signal is not None:
            signal_label = (
                f"{latest_signal.signal.signal_type.name.title()} "
                f"({pd.Timestamp(latest_signal.signal.date).date().isoformat()})"
            )
            signal_confidence = f"{latest_signal.confidence:.0f}%"
        else:
            signal_label = "None"
            signal_confidence = "-"

        rows.append(
            {
                "Ticker": result.ticker,
                "Trend": trend_label,
                "Trend Strength": trend_strength,
                "Regime": regime_label,
                "Regime Confidence": regime_confidence,
                "Last Signal": signal_label,
                "Signal Confidence": signal_confidence,
            }
        )

    return pd.DataFrame(rows)


def show() -> None:
    """
    Render the Dashboard page: a fast summary scan across the watchlist.

    Unlike Stock Analysis (a full deep-dive on demand), this page auto-
    runs a lightweight scan as soon as there's a watchlist to scan, and
    shows a compact table -- trend, regime, and most recent scored signal
    per ticker -- rather than a chart per ticker.
    """
    st.title("🏠 Dashboard")
    st.caption(
        "A fast scan across your watchlist: trend, regime, and the most "
        "recent scored signal for each ticker. For a full deep-dive on one "
        "ticker, use the Stock Analysis page instead."
    )

    watchlist = load_watchlist()

    if not watchlist:
        st.info(
            "Your watchlist is empty. Add tickers on the Watchlists page "
            "to scan them here."
        )
        return

    col1, col2 = st.columns([4, 1])
    with col1:
        st.caption(f"Watching {len(watchlist)} ticker(s): {', '.join(watchlist)}")
    with col2:
        refresh = st.button("🔄 Refresh", use_container_width=True)

    # Cache scan results in session state, keyed to the exact watchlist
    # scanned, so unrelated widget reruns don't silently re-fetch, but a
    # changed watchlist (or an explicit Refresh) does.
    cached_tickers = st.session_state.get("dashboard_scanned_tickers")
    needs_scan = refresh or cached_tickers != watchlist

    if needs_scan:
        with st.spinner("Scanning watchlist..."):
            results = _run_scan(watchlist)
        st.session_state.dashboard_results = results
        st.session_state.dashboard_scanned_tickers = watchlist

    results = st.session_state.get("dashboard_results") or []
    failures = st.session_state.get("dashboard_failures") or {}

    if failures:
        st.warning("Could not scan: " + ", ".join(sorted(failures)))

    if not results:
        st.info("No scan results available.")
        return

    st.divider()
    table = _build_scan_table(results)
    st.dataframe(table, use_container_width=True, hide_index=True)
