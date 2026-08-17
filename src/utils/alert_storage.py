# Import standard library packages.
import json
from pathlib import Path

# Import local packages.
from src.models.alert_rule import AlertRule, TriggeredAlert

# Same Path-based cache file approach as every other *_storage.py module
# in this app (portfolio_storage.py, watchlist_storage.py, ...).
_ALERT_RULES_FILE = Path("cache/alert_rules.json")
_SENT_ALERTS_FILE = Path("cache/sent_alerts.json")
_LATEST_ALERTS_FILE = Path("cache/triggered_alerts.json")


# ----------------------------------------------------------------------
# Alert rules -- what the user has configured (Settings page CRUD).
# ----------------------------------------------------------------------


def load_alert_rules() -> list[AlertRule]:
    """
    Read persisted alert rules from disk.

    Returns:
        The cached rules, or an empty list if the cache is missing,
        unreadable, or contains invalid data. A single malformed rule is
        skipped rather than discarding the whole file.
    """
    if not _ALERT_RULES_FILE.exists():
        return []

    try:
        payload = json.loads(_ALERT_RULES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    rules: list[AlertRule] = []
    for raw in payload.get("rules", []):
        try:
            rules.append(AlertRule.model_validate(raw))
        except Exception:
            continue

    return rules


def save_alert_rules(rules: list[AlertRule]) -> None:
    """Persist the current alert rule list to disk (overwrites)."""
    _ALERT_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"rules": [rule.model_dump(mode="json") for rule in rules]}
    _ALERT_RULES_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ----------------------------------------------------------------------
# Sent-alert dedup tracking -- which TriggeredAlert.dedup_key() values
# have already been emailed, so the scanner doesn't re-send on every run
# against unchanged data. Written/read only by the scanning script.
# ----------------------------------------------------------------------


def load_sent_alert_keys() -> set[str]:
    """
    Read the set of already-sent alert dedup keys from disk.

    Returns:
        The cached keys, or an empty set if the cache is missing,
        unreadable, or contains invalid data.
    """
    if not _SENT_ALERTS_FILE.exists():
        return set()

    try:
        payload = json.loads(_SENT_ALERTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()

    keys = payload.get("keys", [])
    return {key for key in keys if isinstance(key, str)}


def save_sent_alert_keys(keys: set[str]) -> None:
    """Persist the full set of already-sent alert dedup keys (overwrites)."""
    _SENT_ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"keys": sorted(keys)}
    _SENT_ALERTS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# ----------------------------------------------------------------------
# Latest scan results -- what's currently active, for the Dashboard page
# to display. The scanning script runs in a separate process from
# Streamlit, so this is how it hands results to the running app.
# ----------------------------------------------------------------------


def load_latest_alerts() -> list[TriggeredAlert]:
    """
    Read the most recent scan's triggered alerts from disk.

    Returns:
        The cached alerts, or an empty list if none have been scanned
        yet, the cache is unreadable, or contains invalid data.
    """
    if not _LATEST_ALERTS_FILE.exists():
        return []

    try:
        payload = json.loads(_LATEST_ALERTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    alerts: list[TriggeredAlert] = []
    for raw in payload.get("alerts", []):
        try:
            alerts.append(TriggeredAlert.model_validate(raw))
        except Exception:
            continue

    return alerts


def save_latest_alerts(alerts: list[TriggeredAlert]) -> None:
    """
    Persist the current scan's triggered alerts (overwrites -- this is
    always "what's active as of the most recent scan", not a running log).
    """
    _LATEST_ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {"alerts": [alert.model_dump(mode="json") for alert in alerts]}
    _LATEST_ALERTS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
