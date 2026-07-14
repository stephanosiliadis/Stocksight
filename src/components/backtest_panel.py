import streamlit as st


def render_backtest_panel(
    results: dict | None,
):
    st.subheader("Backtest Results")
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
