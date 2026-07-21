import streamlit as st

from src.models.backtest_metrics import ExtendedBacktestMetrics


def render_backtest_panel(
    results: dict | None,
    extended: ExtendedBacktestMetrics | None = None,
):
    """
    Render backtest results as a row of metric cards.

    Args:
        results: Mapping with keys "total_return", "sharpe_ratio",
            "max_drawdown", "win_rate" (pre-formatted display strings).
        extended: Optional extended metrics (Sortino, profit factor,
            expectancy, avg/largest winner and loser). When omitted
            (the default), only the original four metrics are shown --
            existing callers that don't pass this see no change in
            behavior.
    """
    st.subheader("📈 Backtest Results")
    if not results:
        st.info("No backtest available")
        return

    cols = st.columns(4)
    metrics = [
        "total_return",
        "sharpe_ratio",
        "max_drawdown",
        "win_rate",
    ]
    for i, key in enumerate(metrics):
        if key in results:
            with cols[i]:
                st.metric(
                    key.replace("_", " ").title(),
                    results[key],
                )

    if extended is not None:
        _render_extended_metrics(extended)


def _render_extended_metrics(extended: ExtendedBacktestMetrics) -> None:
    """
    Render the second row of extended metrics, when provided.

    Note: all dollar amounts here are placed in st.metric labels/values,
    never in st.caption or st.markdown text -- st.metric renders its
    label/value as plain text, but st.caption/st.markdown run their
    content through Streamlit's markdown renderer, which treats a pair of
    unescaped "$" as inline LaTeX math and can visibly mangle currency
    ranges. Keeping currency text inside st.metric sidesteps that.
    """
    st.caption("Extended Metrics")
    cols = st.columns(4)

    with cols[0]:
        st.metric("Sortino Ratio", f"{extended.sortino_ratio:.2f}")

    with cols[1]:
        is_unbounded = extended.profit_factor >= 999.0
        profit_factor_display = "∞" if is_unbounded else f"{extended.profit_factor:.2f}"
        st.metric("Profit Factor", profit_factor_display)

    with cols[2]:
        st.metric("Expectancy / Trade", f"${extended.expectancy:,.2f}")

    with cols[3]:
        st.metric(
            "Avg Win / Loss",
            f"${extended.avg_winner:,.0f} / ${extended.avg_loser:,.0f}",
        )

    cols2 = st.columns(2)
    with cols2[0]:
        st.metric("Largest Winner", f"${extended.largest_winner:,.2f}")
    with cols2[1]:
        st.metric("Largest Loser", f"-${extended.largest_loser:,.2f}")
