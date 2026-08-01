# Import standard library packages.
from datetime import date

# Import third party packages.
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Import local packages.
from src.components.metrics_cards import render_metrics_cards
from src.models.holding import Holding
from src.models.portfolio import Portfolio
from src.services.data_service import DataService
from src.services.fundamentals_service import FundamentalsService
from src.services.portfolio_service import PortfolioService
from src.utils.portfolio_storage import load_portfolios, save_portfolios
from src.visualization.chart_theme import ChartTheme

# Benchmark ticker used for the "vs. benchmark" comparison. Matches
# RelativeStrengthService's own default, since we're comparing against
# the same thing it does everywhere else in the app.
_BENCHMARK_TICKER = "SPY"


def _get_portfolio_by_name(portfolios: list[Portfolio], name: str) -> Portfolio:
    """Find a portfolio by name in an already-loaded list."""
    for portfolio in portfolios:
        if portfolio.name == name:
            return portfolio
    # Should not happen in normal use (the selector only offers names
    # that exist), but return an empty, unsaved portfolio rather than
    # raising if it ever does.
    return Portfolio(name=name, holdings=[])


def _render_portfolio_selector() -> Portfolio:
    """
    Render the portfolio picker: an existing-portfolio dropdown, plus a
    small "create new" flow. Returns the currently active Portfolio
    (already present in st.session_state.portfolios).
    """
    portfolios = st.session_state.portfolios

    if not portfolios:
        # First-run convenience: start with one default portfolio instead
        # of forcing an empty page with no obvious next step.
        portfolios.append(Portfolio(name="My Portfolio", holdings=[]))
        save_portfolios(portfolios)

    names = [portfolio.name for portfolio in portfolios]

    col1, col2 = st.columns([3, 1])
    with col1:
        active_name = st.selectbox("Portfolio", options=names, key="portfolio_selector")
    with col2:
        st.write("")
        st.write("")
        if st.button("➕ New", use_container_width=True):
            st.session_state.show_new_portfolio_input = True

    if st.session_state.get("show_new_portfolio_input"):
        with st.form(key="new_portfolio_form", clear_on_submit=True):
            new_name = st.text_input("New portfolio name")
            created = st.form_submit_button("Create")
            if created:
                new_name = new_name.strip()
                if not new_name:
                    st.warning("Enter a name for the new portfolio.")
                elif new_name in names:
                    st.warning("A portfolio with that name already exists.")
                else:
                    portfolios.append(Portfolio(name=new_name, holdings=[]))
                    save_portfolios(portfolios)
                    st.session_state.show_new_portfolio_input = False
                    st.session_state.portfolio_selector = new_name
                    st.rerun()

    return _get_portfolio_by_name(portfolios, active_name)


def _render_holdings_form(portfolio: Portfolio) -> None:
    """
    Render the add-holding form, plus the current holdings table with a
    remove button per row.
    """
    st.subheader("Holdings")

    with st.form(key=f"add_holding_{portfolio.name}", clear_on_submit=True):
        cols = st.columns(4)
        with cols[0]:
            ticker = st.text_input("Ticker", placeholder="AAPL")
        with cols[1]:
            shares = st.number_input("Shares", min_value=0.0, step=1.0, value=0.0)
        with cols[2]:
            cost_basis = st.number_input(
                "Cost basis ($/share)", min_value=0.0, step=1.0, value=0.0
            )
        with cols[3]:
            purchase_date = st.date_input("Purchase date", value=date.today())

        submitted = st.form_submit_button("Add Holding")
        if submitted:
            _handle_add_holding(portfolio, ticker, shares, cost_basis, purchase_date)

    if not portfolio.holdings:
        st.info("No holdings yet -- add one above.")
        return

    for index, holding in enumerate(portfolio.holdings):
        cols = st.columns([2, 2, 2, 2, 1])
        cols[0].write(f"**{holding.ticker}**")
        cols[1].write(f"{holding.shares:g} shares")
        cols[2].write(f"${holding.cost_basis:,.2f}/share")
        cols[3].write(holding.purchase_date.isoformat())
        if cols[4].button("✕", key=f"remove_{portfolio.name}_{index}"):
            portfolio.holdings.pop(index)
            save_portfolios(st.session_state.portfolios)
            st.rerun()


def _handle_add_holding(
    portfolio: Portfolio,
    ticker: str,
    shares: float,
    cost_basis: float,
    purchase_date: date,
) -> None:
    """Validate and append a new holding, persisting on success."""
    ticker = ticker.strip().upper()

    if not ticker:
        st.warning("Enter a ticker before adding a holding.")
        return
    if shares <= 0:
        st.warning("Shares must be greater than 0.")
        return

    portfolio.holdings.append(
        Holding(
            ticker=ticker,
            shares=shares,
            cost_basis=cost_basis,
            purchase_date=purchase_date,
        )
    )
    save_portfolios(st.session_state.portfolios)
    st.rerun()


def _fetch_price_data(
    tickers: list[str],
    start_date: date,
    end_date: date,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV data for each ticker, silently skipping any that fail."""
    data_service = DataService()
    price_data = {}

    for ticker in tickers:
        data = data_service.serve_stock_data(
            ticker, start_date.isoformat(), end_date.isoformat()
        )
        if data is not None and not data.empty:
            price_data[ticker] = data

    return price_data


def _fetch_fundamentals(tickers: list[str]) -> dict:
    """Fetch Fundamentals for each ticker, silently skipping any that fail."""
    fundamentals_service = FundamentalsService()
    fundamentals = {}

    for ticker in tickers:
        result = fundamentals_service.serve_fundamentals(ticker)
        if result is not None:
            fundamentals[ticker] = result

    return fundamentals


def _build_sector_pie_chart(sector_allocation: dict[str, float]) -> go.Figure | None:
    """Build a donut chart of sector allocation, using ChartTheme's palette."""
    if not sector_allocation:
        return None

    theme = ChartTheme()
    labels = list(sector_allocation.keys())
    values = list(sector_allocation.values())
    colors = [theme.palette[index % len(theme.palette)] for index in range(len(labels))]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.45,
                marker=dict(colors=colors),
                textinfo="label+percent",
            )
        ]
    )
    fig.update_layout(
        title="Sector Allocation",
        template="plotly_white",
        height=420,
        margin=dict(t=50, b=30, l=30, r=30),
    )
    return fig


def _run_portfolio_analysis(portfolio: Portfolio) -> None:
    """Fetch data and run PortfolioService, stashing the result in session state."""
    tickers = [holding.ticker for holding in portfolio.holdings]
    start_date = min(holding.purchase_date for holding in portfolio.holdings)
    end_date = date.today()

    with st.spinner("Fetching data and analyzing portfolio..."):
        price_data = _fetch_price_data(tickers, start_date, end_date)
        fundamentals = _fetch_fundamentals(tickers)
        benchmark_data = DataService().serve_stock_data(
            _BENCHMARK_TICKER, start_date.isoformat(), end_date.isoformat()
        )

        analysis = PortfolioService().serve_analysis(
            portfolio=portfolio,
            price_data=price_data,
            fundamentals=fundamentals,
            benchmark_data=benchmark_data,
        )

    st.session_state.portfolio_analysis = analysis
    st.session_state.portfolio_analysis_name = portfolio.name


def _render_analysis(portfolio: Portfolio) -> None:
    """Render the Analyze button and, once run, the results."""
    if not portfolio.holdings:
        return

    if st.button("📊 Analyze Portfolio", type="primary"):
        _run_portfolio_analysis(portfolio)

    analysis = st.session_state.get("portfolio_analysis")
    analyzed_name = st.session_state.get("portfolio_analysis_name")
    if analysis is None or analyzed_name != portfolio.name:
        return

    st.divider()
    st.subheader("📈 Portfolio Performance")

    metrics = {
        "Total Value": f"${analysis.total_value:,.2f}",
        "Total Cost": f"${analysis.total_cost:,.2f}",
        "Total Return": f"{analysis.total_return_pct:+.2f}%",
        "Diversification": f"{analysis.diversification_score:.2f}",
    }
    render_metrics_cards(metrics)

    if analysis.benchmark_return_pct is not None:
        st.caption(
            f"Portfolio {analysis.total_return_pct:+.2f}%  •  "
            f"{_BENCHMARK_TICKER} {analysis.benchmark_return_pct:+.2f}%"
        )

    if analysis.sector_allocation:
        chart = _build_sector_pie_chart(analysis.sector_allocation)
        if chart is not None:
            st.plotly_chart(chart, use_container_width=True, key="sector_pie_chart")


def show() -> None:
    """Render the Portfolio page."""
    st.title("💼 Portfolio")
    st.caption(
        "Track real holdings -- shares, cost basis, and purchase date -- to see "
        "allocation, diversification, and performance versus a benchmark. "
        "(A watchlist is just tickers you're watching; a portfolio is actual "
        "positions with real gain/loss -- see the Watchlists page for the former.)"
    )

    if "portfolios" not in st.session_state:
        st.session_state.portfolios = load_portfolios()

    portfolio = _render_portfolio_selector()

    st.divider()
    _render_holdings_form(portfolio)

    st.divider()
    _render_analysis(portfolio)
