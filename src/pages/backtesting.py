# Import third party packages.
import streamlit as st

# Import local packages.
from src.components.backtest_panel import render_backtest_panel
from src.models.analysis_result import AnalysisResult
from src.models.backtest_result import BacktestResult
from src.services.backtest_metrics_service import BacktestMetricsService
from src.visualization.equity_curve_chart import EquityCurveChart


def _render_trade_attribution(
    metrics_service: BacktestMetricsService,
    backtest_result: BacktestResult,
) -> None:
    """
    Render the single best and worst trade from the backtest, if any.

    Currency amounts are kept inside st.metric (plain text), never in
    st.caption/st.markdown, since Streamlit's markdown renderer treats a
    pair of unescaped "$" as inline LaTeX math and can visibly mangle
    currency text -- st.metric doesn't run its label/value through that
    renderer, so it's the safe place for this.
    """
    attribution = metrics_service.serve_trade_attribution(backtest_result)
    best_trade = attribution.get("best_trade")
    worst_trade = attribution.get("worst_trade")

    if best_trade is None and worst_trade is None:
        return

    st.caption("Trade Attribution")
    cols = st.columns(2)

    with cols[0]:
        if best_trade is not None:
            st.metric(
                "Best Trade",
                f"${best_trade.pnl:,.2f}",
                f"{best_trade.entry_date.date()} \u2192 {best_trade.exit_date.date()}",
            )
        else:
            st.metric("Best Trade", "N/A")

    with cols[1]:
        if worst_trade is not None:
            st.metric(
                "Worst Trade",
                f"${worst_trade.pnl:,.2f}",
                f"{worst_trade.entry_date.date()} \u2192 {worst_trade.exit_date.date()}",
            )
        else:
            st.metric("Worst Trade", "N/A")


def _render_ticker_backtest(result: AnalysisResult) -> None:
    """
    Render one ticker's full backtest section: summary metrics, extended
    metrics, trade attribution, and the equity curve chart.

    This reuses render_backtest_panel, BacktestMetricsService, and
    EquityCurveChart exactly as they were used before -- moved here from
    Stock Analysis, not reimplemented. No new backtest math lives on this
    page; it only decides how to lay the existing results out.
    """
    backtest_result = result.backtest_result
    if backtest_result is None:
        return

    st.caption(f"Ticker: {result.ticker}")

    backtest_data = {
        "total_return": f"{backtest_result.total_return:.2f}%",
        "sharpe_ratio": f"{backtest_result.sharpe_ratio:.2f}",
        "max_drawdown": f"{backtest_result.max_drawdown:.2f}%",
        "win_rate": f"{backtest_result.win_rate:.2f}%",
    }

    metrics_service = BacktestMetricsService()
    extended_metrics = metrics_service.calculate(backtest_result)
    render_backtest_panel(backtest_data, extended=extended_metrics)

    _render_trade_attribution(metrics_service, backtest_result)

    equity_chart = EquityCurveChart(backtest_result.equity_curve).build()
    if equity_chart is not None:
        st.divider()
        st.subheader("Equity Curve")
        st.plotly_chart(
            equity_chart,
            use_container_width=True,
            key=f"backtest_equity_{result.ticker}",
        )


def show() -> None:
    """
    Render the Backtesting page.

    Backtests are computed as part of the regular Stock Analysis pipeline
    (toggle "Run backtest" in that page's sidebar, since a backtest needs
    the same price/signal data the rest of the analysis already fetches).
    This page doesn't re-run anything or introduce a second analysis
    flow -- it reads the same st.session_state.analysis_results that page
    already populates, and displays whichever results include a backtest.
    """
    st.title("🧪 Backtesting")
    st.caption(
        "Backtest results from your most recent Stock Analysis run. "
        'Enable "Run backtest" in that page\'s sidebar, then come back here.'
    )

    results: list[AnalysisResult] = st.session_state.get("analysis_results") or []
    backtested_results = [
        result for result in results if result.backtest_result is not None
    ]

    if not backtested_results:
        st.info(
            'No backtest results yet. Go to the Stock Analysis page, enable '
            '"Run backtest" in the sidebar, and run an analysis.'
        )
        return

    if len(backtested_results) == 1:
        _render_ticker_backtest(backtested_results[0])
        return

    tabs = st.tabs([result.ticker for result in backtested_results])
    for tab, result in zip(tabs, backtested_results):
        with tab:
            _render_ticker_backtest(result)
