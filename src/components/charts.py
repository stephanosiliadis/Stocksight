import streamlit as st


def render_chart(chart):
    if chart is None:
        st.warning("No chart available")
        return

    st.plotly_chart(
        chart,
        use_container_width=True,
    )
