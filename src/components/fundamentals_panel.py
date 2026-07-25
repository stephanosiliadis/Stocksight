import streamlit as st

from src.models.analyst_rating import AnalystRating
from src.models.earnings import EarningsEvent
from src.models.insider_transaction import InsiderTransaction
from src.models.sector_benchmark import SectorBenchmark


def render_fundamentals_panel(
    fundamentals: dict | None,
    earnings: list[EarningsEvent] | None = None,
    analyst_rating: AnalystRating | None = None,
    insider_transactions: list[InsiderTransaction] | None = None,
    sector_benchmark: SectorBenchmark | None = None,
):
    """
    Render the fundamentals panel: core valuation metrics, plus optional
    earnings calendar, analyst rating, insider activity, and sector
    benchmark sections.

    Every optional section is skipped cleanly when its data is
    None/empty -- the same "skip if not there" pattern already used
    throughout the app (financial statements, backtest results, trade
    plan). Toggling all four off leaves this panel looking exactly as it
    did before Phase 5.

    Args:
        fundamentals: Pre-formatted label -> display value pairs for the
            core metrics grid (P/E, market cap, etc.), or None/empty.
        earnings: Upcoming earnings calendar entries, if requested.
        analyst_rating: Aggregated analyst sentiment, if requested.
        insider_transactions: Insider buy/sell activity, if requested.
        sector_benchmark: Approximate sector P/E comparison, if
            fundamentals were requested (this piggybacks on
            include_fundamentals rather than its own flag).
    """
    st.subheader("💼 Fundamentals")

    if not fundamentals:
        st.info("No fundamental data")
    else:
        cols = st.columns(3)
        for index, (key, value) in enumerate(fundamentals.items()):
            with cols[index % 3]:
                st.metric(
                    label=key.replace("_", " ").title(),
                    value=value,
                )

    if sector_benchmark is not None:
        _render_sector_benchmark(sector_benchmark)

    if analyst_rating is not None:
        _render_analyst_rating(analyst_rating)

    if earnings:
        _render_earnings(earnings)

    if insider_transactions:
        _render_insider_transactions(insider_transactions)


def _render_sector_benchmark(benchmark: SectorBenchmark) -> None:
    """
    Render the sector P/E comparison. All dollar-free, so no LaTeX-math
    concerns from unescaped "$" pairs here.
    """
    st.markdown("##### Sector P/E Comparison")
    st.caption(
        "Approximate comparison against a handful of sector peers, "
        "not a comprehensive sector index."
    )
    cols = st.columns(3)

    with cols[0]:
        st.metric("Sector", benchmark.sector)

    with cols[1]:
        ticker_pe = (
            f"{benchmark.ticker_pe:.2f}" if benchmark.ticker_pe is not None else "N/A"
        )
        st.metric("Ticker P/E", ticker_pe)

    with cols[2]:
        avg_pe = f"{benchmark.avg_pe:.2f}" if benchmark.avg_pe is not None else "N/A"
        st.metric("Peer Avg P/E", avg_pe)

    if benchmark.pe_percentile is not None:
        st.caption(f"Percentile vs. peers: {benchmark.pe_percentile:.0f}th")


def _render_analyst_rating(rating: AnalystRating) -> None:
    """
    Render aggregated analyst sentiment. Price targets are kept inside
    st.metric (plain text) rather than st.caption/st.markdown, since
    Streamlit's markdown renderer treats a pair of unescaped "$" as
    inline LaTeX math and can visibly mangle currency ranges.
    """
    st.markdown("##### Analyst Ratings")
    cols = st.columns(4)

    with cols[0]:
        st.metric("Consensus", rating.consensus)

    with cols[1]:
        st.metric("# Analysts", rating.num_analysts)

    with cols[2]:
        mean_target = (
            f"${rating.price_target_mean:.2f}"
            if rating.price_target_mean is not None
            else "N/A"
        )
        st.metric("Price Target (Mean)", mean_target)

    with cols[3]:
        low = (
            f"${rating.price_target_low:.2f}"
            if rating.price_target_low is not None
            else "N/A"
        )
        high = (
            f"${rating.price_target_high:.2f}"
            if rating.price_target_high is not None
            else "N/A"
        )
        st.metric("Target Range", f"{low} \u2013 {high}")


def _render_earnings(earnings: list[EarningsEvent]) -> None:
    """Render the upcoming earnings calendar as a table."""
    st.markdown("##### Earnings Calendar")
    table = [
        {
            "Date": event.date.isoformat(),
            "Type": "Estimate" if event.is_estimate else "Actual",
            "EPS Estimate": (
                f"{event.eps_estimate:.2f}" if event.eps_estimate is not None else "N/A"
            ),
            "EPS Actual": (
                f"{event.eps_actual:.2f}" if event.eps_actual is not None else "N/A"
            ),
        }
        for event in earnings
    ]
    st.table(table)


def _render_insider_transactions(transactions: list[InsiderTransaction]) -> None:
    """Render insider buy/sell activity as a table."""
    st.markdown("##### Insider Activity")
    table = [
        {
            "Date": txn.date.isoformat(),
            "Insider": txn.insider_name,
            "Type": txn.transaction_type,
            "Shares": f"{txn.shares:,}",
            "Value": f"${txn.value:,.2f}" if txn.value is not None else "N/A",
        }
        for txn in transactions
    ]
    st.table(table)
