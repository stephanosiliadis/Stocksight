import streamlit as st


def render_date_selector():
    st.subheader("Period")
    period = st.selectbox(
        "Frequency",
        [
            "Daily",
            "Weekly",
            "Monthly",
            "Custom",
        ],
    )
    if period == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input(
                "Start date",
            )

        with col2:
            end = st.date_input(
                "End date",
            )

        return {
            "frequency": period,
            "start": start,
            "end": end,
        }

    return {
        "frequency": period,
        "start": None,
        "end": None,
    }
