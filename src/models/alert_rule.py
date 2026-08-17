from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator

ConditionType = Literal[
    "price_above", "price_below", "rsi_above", "rsi_below", "new_signal"
]

# Condition types that compare a live value against a numeric threshold.
# "new_signal" is the odd one out -- it just asks "did a signal appear?"
_THRESHOLD_CONDITIONS = {"price_above", "price_below", "rsi_above", "rsi_below"}


class AlertRule(BaseModel):
    """
    A user-defined condition to watch for on one ticker.

    Attributes:
        ticker: Stock ticker symbol this rule applies to.
        condition_type: What to check -- 'price_above'/'price_below'
            compare the latest Close, 'rsi_above'/'rsi_below' compare the
            latest RSI, 'new_signal' fires whenever the analysis has any
            signal in its (already date-filtered) signals list.
        threshold: Required for every condition_type except 'new_signal',
            which ignores it.
    """

    ticker: str
    condition_type: ConditionType
    threshold: float | None = None

    @model_validator(mode="after")
    def _validate_threshold(self) -> "AlertRule":
        if self.condition_type in _THRESHOLD_CONDITIONS and self.threshold is None:
            raise ValueError(
                f"threshold is required for condition_type={self.condition_type!r}"
            )
        return self


class TriggeredAlert(BaseModel):
    """
    A single firing of an AlertRule.

    Attributes:
        rule: The AlertRule that fired.
        triggered_at: When the underlying condition was true. Derived
            from the data itself (the latest bar's date, or the
            triggering signal's date) rather than wall-clock time, so
            that re-checking the same unchanged AnalysisResult produces
            an identical TriggeredAlert -- this is what makes dedup_key()
            stable across repeated scans of unchanged data.
        message: Human-readable description of what fired.
    """

    rule: AlertRule
    triggered_at: datetime
    message: str

    def dedup_key(self) -> str:
        """
        Stable identity for "have I already sent this exact alert".

        Built from the rule's own identity plus triggered_at (which is
        itself derived from the data, not wall-clock time) -- so the same
        rule firing again against unchanged data produces the same key,
        while a genuinely new trigger (new date, new signal) produces a
        different one.
        """
        return (
            f"{self.rule.ticker}|{self.rule.condition_type}|"
            f"{self.rule.threshold}|{self.triggered_at.isoformat()}"
        )
