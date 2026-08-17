# Import third party packages.
import streamlit as st

# Import local packages.
from src.components.indicator_selector import AVAILABLE_INDICATORS
from src.models.alert_rule import AlertRule
from src.models.app_settings import AppSettings
from src.utils.alert_storage import load_alert_rules, save_alert_rules
from src.utils.settings_storage import load_settings, save_settings

_CONDITION_LABELS = {
    "price_above": "Price above",
    "price_below": "Price below",
    "rsi_above": "RSI above",
    "rsi_below": "RSI below",
    "new_signal": "New signal",
}
_THRESHOLD_CONDITIONS = {"price_above", "price_below", "rsi_above", "rsi_below"}


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
    st.caption("Pre-filled in the Trade Plan risk inputs on the Stock Analysis page.")

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


def _handle_add_rule(
    ticker: str, condition_label: str, threshold: float | None
) -> None:
    """Validate and append a new alert rule, persisting on success."""
    ticker = ticker.strip().upper()
    condition_type = next(
        key for key, label in _CONDITION_LABELS.items() if label == condition_label
    )

    if not ticker:
        st.warning("Enter a ticker before adding a rule.")
        return

    try:
        rule = AlertRule(
            ticker=ticker,
            condition_type=condition_type,
            threshold=threshold if condition_type in _THRESHOLD_CONDITIONS else None,
        )
    except Exception as exc:
        st.warning(f"Could not create rule: {exc}")
        return

    st.session_state.alert_rules.append(rule)
    save_alert_rules(st.session_state.alert_rules)
    st.rerun()


def _render_add_rule_form() -> None:
    """Render the add-alert-rule form."""
    with st.form(key="add_alert_rule", clear_on_submit=True):
        cols = st.columns([2, 2, 2, 1])
        with cols[0]:
            ticker = st.text_input("Ticker", placeholder="AAPL")
        with cols[1]:
            condition_label = st.selectbox(
                "Condition", list(_CONDITION_LABELS.values())
            )
        with cols[2]:
            is_threshold_condition = condition_label != _CONDITION_LABELS["new_signal"]
            threshold = st.number_input(
                "Threshold",
                value=0.0,
                step=1.0,
                disabled=not is_threshold_condition,
                help="Price ($) or RSI value, depending on the condition.",
            )
        with cols[3]:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("Add", use_container_width=True)

        if submitted:
            _handle_add_rule(ticker, condition_label, threshold)


def _render_alert_rules_table() -> None:
    """Render existing alert rules with a remove button per row."""
    rules = st.session_state.alert_rules

    if not rules:
        st.info("No alert rules yet -- add one above.")
        return

    for index, rule in enumerate(rules):
        cols = st.columns([2, 3, 2, 1])
        cols[0].write(f"**{rule.ticker}**")
        cols[1].write(_CONDITION_LABELS[rule.condition_type])
        cols[2].write(f"{rule.threshold:g}" if rule.threshold is not None else "-")
        if cols[3].button("✕", key=f"remove_alert_rule_{index}"):
            st.session_state.alert_rules.pop(index)
            save_alert_rules(st.session_state.alert_rules)
            st.rerun()


def _render_alerts_section() -> None:
    """
    Render the Alerts section: add/remove AlertRule entries.

    These rules are read by scripts/run_watchlist_scan.py (run outside
    Streamlit, on a schedule) -- this page only edits the persisted rule
    list, it doesn't run any scan itself.
    """
    st.subheader("Alerts")
    st.caption(
        "Rules checked by the watchlist scanner "
        "(scripts/run_watchlist_scan.py, run on a schedule outside the app). "
        "Triggered alerts show up on the Dashboard page."
    )

    if "alert_rules" not in st.session_state:
        st.session_state.alert_rules = load_alert_rules()

    _render_add_rule_form()
    _render_alert_rules_table()


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
    _render_alerts_section()

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
