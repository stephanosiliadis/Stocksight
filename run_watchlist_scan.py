#!/usr/bin/env python3
"""
Standalone watchlist alert scanner.

WHY A STANDALONE SCRIPT INSTEAD OF AN IN-APP POLLING LOOP:
Streamlit only runs code while a user has the page open and interacting
with it -- there is no built-in background job runner. An in-app polling
loop (e.g. st_autorefresh) would therefore only check conditions while
someone happens to have a browser tab open, which defeats the purpose of
an alert: the whole point is to be notified about something that happened
while you *weren't* watching. This script is meant to be triggered by an
OS-level scheduler instead, so it runs on a real schedule independent of
whether the Streamlit app is open at all.

USAGE:
    Run directly from a terminal, entirely outside Streamlit:
        python scripts/run_watchlist_scan.py

    Or on a schedule via cron (Linux/Mac), e.g. every 15 minutes on
    weekdays during market hours:
        */15 9-16 * * 1-5 cd /path/to/project && \
            ALERT_NOTIFY_EMAIL=you@example.com python scripts/run_watchlist_scan.py

    Or via Windows Task Scheduler, pointing the "Program" at your Python
    interpreter and "Arguments" at this script's path.

CONFIGURATION:
    ALERT_NOTIFY_EMAIL   Address to email triggered alerts to. If unset,
                          alerts are still detected and persisted for the
                          Dashboard page, but no email is sent (dry run).
    SMTP_HOST/PORT/USERNAME/PASSWORD
                          See notification_service.py -- required for
                          actually sending email, not required to run
                          the scan itself.
"""

# Import standard library packages.
import os
import sys
from pathlib import Path

# Ensure the project root is importable when this script is run directly
# (`python scripts/run_watchlist_scan.py`) rather than via `python -m`,
# since it isn't installed as a package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import local packages.
from src.models.analysis_request import AnalysisRequest  # noqa: E402
from src.models.alert_rule import TriggeredAlert  # noqa: E402
from src.services.alert_service import AlertService  # noqa: E402
from src.services.analysis_service import AnalysisService  # noqa: E402
from src.services.notification_service import NotificationService  # noqa: E402
from src.utils.alert_storage import (  # noqa: E402
    load_alert_rules,
    load_sent_alert_keys,
    save_latest_alerts,
    save_sent_alert_keys,
)
from src.utils.watchlist_storage import load_watchlist  # noqa: E402

# Kept light on purpose: enough indicators for every AlertRule condition
# type to be checkable (rsi_above/below needs RSI; new_signal needs
# whichever indicators the active Signal detectors require -- RSI, MACD,
# and EMA50/EMA200 crosses), without fetching fundamentals, statements,
# or running a backtest for what is just a condition check.
_SCAN_PERIOD = "3m"
_SCAN_INDICATORS = ["rsi", "macd", "ema50", "ema200"]


def run_scan(notify_email: str | None = None) -> list[TriggeredAlert]:
    """
    Scan every watchlist ticker against every saved AlertRule, email any
    newly-triggered alert (skipping ones already sent for this exact
    trigger), and persist the full set of currently-active alerts for
    the Dashboard page to display.

    Args:
        notify_email: Address to send notification emails to. If None,
            alerts are still detected and persisted, just not emailed --
            useful for a dry run or when notifications aren't configured.

    Returns:
        Every TriggeredAlert from this scan (not just the newly-sent
        ones), which is also what gets persisted for the Dashboard.
    """
    watchlist = load_watchlist()
    rules = load_alert_rules()

    if not watchlist or not rules:
        save_latest_alerts([])
        return []

    request = AnalysisRequest(
        tickers=watchlist,
        period=_SCAN_PERIOD,
        indicators=_SCAN_INDICATORS,
        include_fundamentals=False,
        include_statements=False,
        include_earnings=False,
        include_analyst_ratings=False,
        include_insider_activity=False,
        backtest=False,
    )

    analysis_service = AnalysisService()
    results = analysis_service.analyze(request)

    alert_service = AlertService()
    all_triggered: list[TriggeredAlert] = []
    for result in results:
        all_triggered.extend(alert_service.check_conditions(result, rules))

    _send_new_alerts(all_triggered, notify_email)
    save_latest_alerts(all_triggered)

    return all_triggered


def _send_new_alerts(
    triggered: list[TriggeredAlert],
    notify_email: str | None,
) -> None:
    """
    Email whichever triggered alerts haven't already been sent, tracking
    dedup keys so re-running the scan against unchanged data doesn't
    re-email the same trigger.
    """
    already_sent = load_sent_alert_keys()
    updated_sent = set(already_sent)

    if notify_email:
        notifier = NotificationService()
        for alert in triggered:
            key = alert.dedup_key()
            if key in already_sent:
                continue

            try:
                notifier.send_email(
                    to=notify_email,
                    subject=f"Stocksight Alert: {alert.rule.ticker}",
                    body=alert.message,
                )
                updated_sent.add(key)
            except Exception as exc:
                # One failed send (bad credentials, provider hiccup)
                # should not stop the rest of the batch from being
                # attempted, and should not be recorded as sent.
                print(
                    f"Failed to send alert for {alert.rule.ticker}: {exc}",
                    file=sys.stderr,
                )

    save_sent_alert_keys(updated_sent)


def main() -> None:
    notify_email = os.environ.get("ALERT_NOTIFY_EMAIL")
    triggered = run_scan(notify_email=notify_email)

    print(f"Scan complete: {len(triggered)} alert(s) currently active.")
    for alert in triggered:
        print(f"  - {alert.message}")

    if not notify_email:
        print(
            "ALERT_NOTIFY_EMAIL not set -- alerts detected and saved for "
            "the Dashboard, but no email was sent."
        )


if __name__ == "__main__":
    main()
