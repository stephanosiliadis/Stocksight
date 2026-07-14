import streamlit as st
from src.components.ticker_input import render_ticker_input
from src.components.indicator_selector import render_indicator_selector
from src.components.date_selector import render_date_selector
from src.components.charts import render_chart
from src.components.financials_panel import render_financials_panel
from src.components.metrics_cards import render_metrics_cards


def show():
    st.title("Stock Analysis")
    tickers = render_ticker_input()
    if not tickers:
        return

    indicators = render_indicator_selector()
    period = render_date_selector()
    if st.button("Analyze"):
        # Call AnalysisService here
        results = ...
        for result in results:
            st.header(result.ticker)
            render_chart(result.chart)
            render_financials_panel(result.financials)
            render_metrics_cards(result.statistics)
