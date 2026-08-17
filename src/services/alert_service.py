from __future__ import annotations

import pandas as pd

from src.models.alert_rule import AlertRule, TriggeredAlert
from src.models.analysis_result import AnalysisResult


class AlertService:
    """
    Matches AlertRules against an AnalysisResult.

    Pure function of its inputs -- no scheduling, no email, no state
    beyond what's passed in. Given the same AnalysisResult and rules, it
    always returns the same TriggeredAlerts (see TriggeredAlert's
    triggered_at docstring for why that determinism matters for dedup).
    """

    def check_conditions(
        self,
        result: AnalysisResult,
        rules: list[AlertRule],
    ) -> list[TriggeredAlert]:
        """
        Check every rule for this ticker against the given AnalysisResult.

        Args:
            result: Analysis output to check conditions against.
            rules: Rules to evaluate. Rules for a different ticker than
                result.ticker are silently skipped (callers scanning a
                whole watchlist typically pass every rule for every
                result; this makes that the natural way to call it).

        Returns:
            One TriggeredAlert per rule whose condition is currently
            true. Empty list if nothing fired -- never raises.
        """
        triggered: list[TriggeredAlert] = []

        for rule in rules:
            if rule.ticker != result.ticker:
                continue

            alert = self._check_rule(result, rule)
            if alert is not None:
                triggered.append(alert)

        return triggered

    def _check_rule(
        self,
        result: AnalysisResult,
        rule: AlertRule,
    ) -> TriggeredAlert | None:
        """Dispatch to the right check for this rule's condition_type."""
        if rule.condition_type == "price_above":
            return self._check_price(result, rule, above=True)
        if rule.condition_type == "price_below":
            return self._check_price(result, rule, above=False)
        if rule.condition_type == "rsi_above":
            return self._check_rsi(result, rule, above=True)
        if rule.condition_type == "rsi_below":
            return self._check_rsi(result, rule, above=False)
        if rule.condition_type == "new_signal":
            return self._check_new_signal(result, rule)
        return None

    def _check_price(
        self,
        result: AnalysisResult,
        rule: AlertRule,
        above: bool,
    ) -> TriggeredAlert | None:
        """price_above / price_below: compare the latest Close to threshold."""
        if rule.threshold is None:
            return None

        data = result.raw_data
        if data is None or data.empty or "Close" not in data.columns:
            return None

        close_series = data["Close"].dropna()
        if close_series.empty:
            return None

        latest_close = float(close_series.iloc[-1])
        latest_date = pd.Timestamp(close_series.index[-1]).to_pydatetime()

        condition_met = (
            latest_close > rule.threshold if above else latest_close < rule.threshold
        )
        if not condition_met:
            return None

        direction = "above" if above else "below"
        message = (
            f"{result.ticker}: price ${latest_close:.2f} is {direction} "
            f"${rule.threshold:.2f}"
        )
        return TriggeredAlert(rule=rule, triggered_at=latest_date, message=message)

    def _check_rsi(
        self,
        result: AnalysisResult,
        rule: AlertRule,
        above: bool,
    ) -> TriggeredAlert | None:
        """rsi_above / rsi_below: compare the latest RSI to threshold."""
        if rule.threshold is None:
            return None

        data = result.indicators
        if data is None or data.empty or "RSI" not in data.columns:
            return None

        rsi_series = data["RSI"].dropna()
        if rsi_series.empty:
            return None

        latest_rsi = float(rsi_series.iloc[-1])
        latest_date = pd.Timestamp(rsi_series.index[-1]).to_pydatetime()

        condition_met = (
            latest_rsi > rule.threshold if above else latest_rsi < rule.threshold
        )
        if not condition_met:
            return None

        direction = "above" if above else "below"
        message = (
            f"{result.ticker}: RSI {latest_rsi:.1f} is {direction} "
            f"{rule.threshold:.1f}"
        )
        return TriggeredAlert(rule=rule, triggered_at=latest_date, message=message)

    def _check_new_signal(
        self,
        result: AnalysisResult,
        rule: AlertRule,
    ) -> TriggeredAlert | None:
        """
        new_signal: fires on the most recent signal in result.signals.

        This service has no memory of prior scans, so it can't itself
        tell "new since last check" from "the same signal I saw last
        time" -- it just reports the latest signal present. Suppressing
        repeat alerts for the same signal across scans is the scanning
        script's job (via TriggeredAlert.dedup_key(), which incorporates
        the signal's own date).
        """
        if not result.signals:
            return None

        latest_signal = max(result.signals, key=lambda signal: signal.date)
        message = (
            f"{result.ticker}: new {latest_signal.signal_type.value} signal "
            f"({latest_signal.reason})"
        )
        return TriggeredAlert(
            rule=rule,
            triggered_at=latest_signal.date,
            message=message,
        )
