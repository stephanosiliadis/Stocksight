import streamlit as st

AVAILABLE_INDICATORS = {
    "bollinger": "Bollinger Bands",
    "ema20": "EMA 20",
    "ema50": "EMA 50",
    "ema200": "EMA 200",
    "rsi": "RSI",
    "stochastic": "Stochastic",
    "macd": "MACD",
    "volume": "Volume",
    "atr": "ATR",
}


def render_indicator_selector(
    defaults: list[str] | None = None,
) -> list[str]:

    defaults = defaults or []
    st.subheader("Indicators")
    active = []
    for key, label in AVAILABLE_INDICATORS.items():
        checked = st.checkbox(
            label,
            value=key in defaults,
            key=f"indicator_{key}",
        )
        if checked:
            active.append(key)

    return active
