# Import third party packages.
import streamlit as st

# Import local packages.
from src.components.indicator_selector import AVAILABLE_INDICATORS
from src.models.app_settings import AppSettings
from src.utils.settings_storage import load_settings, save_settings


def _render_indicator_defaults(settings: AppSettings) -> list[str]:
    """Render the default-indicators checkboxes, pre-checked from settings."""
    st.subheader("Default Indicators")
    st.caption("Pre-checked on the Stock Analysis page's indicator selector.")

    selected = []
    cols = st.columns(3)
    for index, (key, label) in enumerate(AVAILABLE_INDICATORS.items()):
        with cols[index % 3]:
            checked = st.checkbox(
                label,
                value=key in settings.default_indicators,
                key=f"settings_indicator_{key}",
            )
            if checked:
                selected.append(key)

    return selected


def _render_risk_defaults(settings: AppSettings) -> tuple[float, float]:
    """Render the default account size / risk % inputs, from settings."""
    st.subheader("Default Trade Plan Inputs")
    st.caption(
        "Pre-filled in the Trade Plan risk inputs on the Stock Analysis page."
    )

    col1, col2 = st.columns(2)
    with col1:
        account_size = st.number_input(
            "Default account size ($)",
            min_value=100.0,
            value=settings.default_account_size,
            step=500.0,
            key="settings_account_size",
        )
    with col2:
        risk_pct_whole = st.number_input(
            "Default risk per trade (%)",
            min_value=0.1,
            max_value=100.0,
            value=settings.default_risk_pct * 100.0,
            step=0.1,
            key="settings_risk_pct",
        )

    return account_size, risk_pct_whole / 100.0


def show() -> None:
    """
    Render the Settings page: application-wide preferences.

    Everything here is just a persisted default -- other pages (Stock
    Analysis's indicator selector and Trade Plan inputs) read these
    values as their starting point but the user can still change them
    per-run; nothing here forces a value anywhere.
    """
    st.title("⚙️ Settings")
    st.caption("Preferences used as defaults across the app.")

    if "app_settings" not in st.session_state:
        st.session_state.app_settings = load_settings()

    settings = st.session_state.app_settings

    st.divider()
    selected_indicators = _render_indicator_defaults(settings)

    st.divider()
    account_size, risk_pct = _render_risk_defaults(settings)

    st.divider()
    if st.button("💾 Save Settings", type="primary"):
        if not selected_indicators:
            st.warning("Select at least one default indicator before saving.")
        else:
            updated = AppSettings(
                default_indicators=selected_indicators,
                default_account_size=account_size,
                default_risk_pct=risk_pct,
            )
            save_settings(updated)
            st.session_state.app_settings = updated
            st.success("Settings saved.")
