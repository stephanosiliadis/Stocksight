import streamlit as st


def render_fundamentals_panel(
    fundamentals: dict | None,
):
    st.subheader("Fundamentals")
    if not fundamentals:
        st.info("No fundamental data")
        return

    cols = st.columns(3)
    for index, (key, value) in enumerate(fundamentals.items()):
        with cols[index % 3]:
            st.metric(
                label=key.replace("_", " ").title(),
                value=value,
            )
