import streamlit as st
import pandas as pd


def render_financials_panel(
    financials: dict | None,
):
    st.subheader("📑 Financial Statements")
    if not financials:
        st.info("Financial data unavailable")
        return

    for name, dataframe in financials.items():
        st.markdown(f"### {name.replace('_', ' ').title()}")
        if isinstance(
            dataframe,
            pd.DataFrame,
        ):
            st.dataframe(
                dataframe,
                use_container_width=True,
            )
