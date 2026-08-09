import streamlit as st

from src.models.risk_profile import TradePlan


def render_risk_inputs(
    key_prefix: str,
    default_account_size: float = 10_000.0,
    default_risk_pct_pct: float = 1.0,
) -> tuple[float, float]:
    """
    Render the account size / risk % input form.

    Args:
        key_prefix: Unique prefix for widget keys, so multiple tickers'
            forms on the same page don't collide (e.g. the ticker symbol).
        default_account_size: Pre-filled account size ($). Callers can
            source this from Settings; defaults to the value this form
            always used before Settings existed.
        default_risk_pct_pct: Pre-filled risk per trade, as a WHOLE
            PERCENT (1.0 == 1%), matching the widget's own units -- not
            the fraction convention used elsewhere. Defaults to the value
            this form always used before Settings existed.

    Returns:
        Tuple of (account_size, risk_pct). risk_pct is a FRACTION
        (0.01 == 1% risk), matching the convention used throughout
        risk_profile.py, PositionSizingService, and TradePlanService.
    """
    col1, col2 = st.columns(2)

    with col1:
        account_size = st.number_input(
            "Account size ($)",
            min_value=100.0,
            value=default_account_size,
            step=500.0,
            key=f"{key_prefix}_account_size",
        )

    with col2:
        risk_pct_whole = st.number_input(
            "Risk per trade (%)",
            min_value=0.1,
            max_value=100.0,
            value=default_risk_pct_pct,
            step=0.1,
            key=f"{key_prefix}_risk_pct",
            help="Percentage of account size risked on this single trade.",
        )

    # UI collects a whole percent (e.g. "1.0" meaning 1%) since that's the
    # natural way for a person to type it, but the rest of the app works
    # in fractions (0.01), so convert once, here, at the boundary.
    risk_pct = risk_pct_whole / 100.0

    return account_size, risk_pct


def render_trade_plan(plan: TradePlan | None) -> None:
    """
    Render a computed TradePlan as a grid of st.metric cards.

    Args:
        plan: The trade plan to render, or None if a plan could not be
            built (e.g. missing/invalid price data) -- in which case an
            informational message is shown instead, following the same
            "skip cleanly when data isn't there" pattern used by the
            other panels in this app.
    """
    st.subheader("Trade Plan")

    if plan is None:
        st.info("Not enough data to build a trade plan for this ticker.")
        return

    row1 = st.columns(4)
    row1[0].metric("Entry Price", f"${plan.entry_price:,.2f}")
    row1[1].metric(
        "Stop Loss",
        f"${plan.stop.stop_price:,.2f}",
        help=f"Method: {plan.stop.method}",
    )
    row1[2].metric("Target", f"${plan.target:,.2f}")
    row1[3].metric("Risk / Reward", f"{plan.risk_reward:.2f}")

    row2 = st.columns(4)
    row2[0].metric("Shares", f"{plan.position_size.shares:,}")
    row2[1].metric("Position Size", f"${plan.position_size.dollar_amount:,.2f}")
    row2[2].metric("Amount At Risk", f"${plan.position_size.risk_amount:,.2f}")
    row2[3].metric("Risk %", f"{plan.position_size.risk_pct * 100:.2f}%")

    st.caption(f"Stop method: **{plan.stop.method}**")
