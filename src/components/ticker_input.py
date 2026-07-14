import streamlit as st


def render_ticker_input() -> list[str]:
    """
    Render ticker input and selected ticker list.

    Returns:
        Current selected tickers.
    """

    if "selected_tickers" not in st.session_state:
        st.session_state.selected_tickers = []

    st.subheader("Ticker Selection")
    col1, col2 = st.columns([4, 1])
    with col1:
        ticker = st.text_input(
            "Enter ticker",
            placeholder="AAPL",
        )

    with col2:
        st.write("")
        if st.button("Add"):
            ticker = ticker.upper().strip()

            if ticker and ticker not in st.session_state.selected_tickers:
                st.session_state.selected_tickers.append(ticker)

    st.markdown("### Selected Tickers")
    if not st.session_state.selected_tickers:
        st.info("No tickers selected")
    else:
        for ticker in st.session_state.selected_tickers:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.write(ticker)

            with col2:
                if st.button(
                    "✕",
                    key=f"remove_{ticker}",
                ):
                    st.session_state.selected_tickers.remove(ticker)
                    st.rerun()

    return st.session_state.selected_tickers
