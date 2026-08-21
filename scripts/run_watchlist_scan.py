#!/usr/bin/env python3
"""
Standalone watchlist alert scanner.

USAGE:
    Run directly from a terminal:
        python scripts/run_watchlist_scan.py

    Or schedule via cron / Windows Task Scheduler to receive local 
    desktop notifications whenever alert rules trigger.
"""

# Import standard library packages.
import sys
from pathlib import Path

# Ensure the project root is importable when this script is run directly.
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

_SCAN_PERIOD = "3m"
_SCAN_INDICATORS = ["rsi", "macd", "ema50", "ema200"]


def run_scan() -> list[TriggeredAlert]:
    """
    Scan every watchlist ticker against every saved AlertRule, dispatch
    a desktop notification for any newly-triggered alert, and persist 
    the full set of currently-active alerts for the Dashboard page.

    Returns:
        Every TriggeredAlert from this scan.
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

    _send_new_alerts(all_triggered)
    save_latest_alerts(all_triggered)

    return all_triggered


def _send_new_alerts(triggered: list[TriggeredAlert]) -> None:
    """
    Trigger desktop notifications for alerts that haven't been sent yet,
    tracking dedup keys so repeated scans don't produce duplicate popups.
    """
    already_sent = load_sent_alert_keys()
    updated_sent = set(already_sent)

    notifier = NotificationService()
    for alert in triggered:
        key = alert.dedup_key()
        if key in already_sent:
            continue

        success = notifier.send_notification(
            title=f"Stocksight Alert: {alert.rule.ticker}",
            message=alert.message,
        )

        if success:
            updated_sent.add(key)

    save_sent_alert_keys(updated_sent)


def main() -> None:
    triggered = run_scan()
    notifier = NotificationService()
    notifier.send_notification(
        title="Stocksight: Scan Complete",
        message=f"Scan complete: {len(triggered)} alert(s) currently active.",
    )


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
