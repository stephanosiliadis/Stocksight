# Import third party packages.
import streamlit as st

# Import local packages.
from src.utils.watchlist_storage import load_watchlist, save_watchlist


def _handle_add_ticker(ticker: str) -> None:
    """Validate, add, and persist a new ticker."""
    ticker = ticker.strip().upper()

    if not ticker:
        st.warning("Enter a ticker before adding it.")
        return

    if ticker in st.session_state.watchlist_tickers:
        st.warning(f"{ticker} is already on the watchlist.")
        return

    st.session_state.watchlist_tickers.append(ticker)
    save_watchlist(st.session_state.watchlist_tickers)
    st.rerun()


def _render_add_form() -> None:
    """Render the add-ticker form."""
    with st.form(key="add_watchlist_ticker", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            ticker = st.text_input(
                "Ticker",
                placeholder="AAPL",
                label_visibility="collapsed",
            )
        with col2:
            submitted = st.form_submit_button("Add", use_container_width=True)

        if submitted:
            _handle_add_ticker(ticker)


def _render_watchlist_table() -> None:
    """Render the current watchlist with a remove button per row."""
    tickers = st.session_state.watchlist_tickers

    if not tickers:
        st.info("Your watchlist is empty -- add a ticker above.")
        return

    for ticker in tickers:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.write(f"**{ticker}**")
        with col2:
            if st.button("✕", key=f"remove_watchlist_{ticker}"):
                st.session_state.watchlist_tickers.remove(ticker)
                save_watchlist(st.session_state.watchlist_tickers)
                st.rerun()


def show() -> None:
    """
    Render the Watchlists page.

    Deliberately just a flat list of tickers -- no shares, no cost basis,
    no P&L. That's what the Portfolio page is for; a watchlist is only
    "tickers I'm keeping an eye on", nothing more. Keeping these as
    separate pages/models (rather than merging them because they both
    involve "a list of tickers") is intentional -- see Phase 6.

    The Dashboard page scans whatever is saved here.
    """
    st.title("⭐ Watchlists")
    st.caption(
        "Track tickers you're keeping an eye on. For actual holdings with "
        "shares and cost basis, see the Portfolio page instead."
    )

    if "watchlist_tickers" not in st.session_state:
        st.session_state.watchlist_tickers = load_watchlist()

    st.divider()
    _render_add_form()

    st.divider()
    st.subheader(f"Watchlist ({len(st.session_state.watchlist_tickers)})")
    _render_watchlist_table()
