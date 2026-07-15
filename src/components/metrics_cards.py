import streamlit as st


def render_metrics_cards(
    metrics: dict,
    deltas: dict | None = None,
):
    """
    Render a row of st.metric cards.

    Args:
        metrics: Mapping of label to the main (large-font) value.
        deltas: Optional mapping of label to secondary text (small-font,
            shown below the value). Useful for things like a date
            associated with a price, which would overflow/clip if put
            in `value` itself. Keys not present here get no delta.
    """
    deltas = deltas or {}
    cols = st.columns(4)
    for index, (name, value) in enumerate(metrics.items()):
        with cols[index % 4]:
            st.metric(
                label=name,
                value=value,
                delta=deltas.get(name),
                delta_color="off",
            )
