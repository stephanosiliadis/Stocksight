import streamlit as st


def render_metrics_cards(
    metrics: dict,
):
    cols = st.columns(4)
    for index, (name, value) in enumerate(metrics.items()):
        with cols[index % 4]:
            st.metric(
                label=name,
                value=value,
            )
