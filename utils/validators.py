"""
validators.py -- pre-flight input validation for the stocktool CLI.

All checks run BEFORE any network call so users get a clear, fast error
instead of a half-completed analysis. ``ValidationError`` carries a
user-facing message; callers should print ``str(exc)`` and exit cleanly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional


class ValidationError(Exception):
    """Raised by input validators so the CLI can print a friendly message."""


def _parse_iso_date(value: str, field: str) -> datetime:
    """Parse an ISO ``YYYY-MM-DD`` string into a ``datetime`` or raise."""
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError(
            f"Invalid {field} '{value}' -- expected YYYY-MM-DD."
        ) from exc


def validate_tickers(
    tickers: Iterable[str], ticker_re=None
) -> list[str]:
    """Return the cleaned, deduped, upper-cased ticker list or raise.

    Args:
        tickers:   Raw ticker strings (already split on comma by the caller).
        ticker_re: Compiled regex describing the allowed ticker format.
                   Defaults to ``<letters>(.<letters>)?`` (e.g. ``AAPL`` or
                   ``SHOP.TO``), matching the interactive wizard.
    """
    import re

    if ticker_re is None:
        ticker_re = re.compile(r"^[A-Za-z]+(\.[A-Za-z]+)?$")

    cleaned: list[str] = []
    seen: set[str] = set()
    for raw in tickers:
        if raw is None:
            continue
        t = raw.strip().upper()
        if not t:
            continue
        if not ticker_re.match(t):
            raise ValidationError(
                f"Invalid ticker format: '{raw}'."
            )
        if t in seen:
            raise ValidationError(
                f"Duplicate ticker: '{t}'. Remove duplicates before running."
            )
        seen.add(t)
        cleaned.append(t)

    if not cleaned:
        raise ValidationError("At least one ticker is required.")

    return cleaned


def validate_period(
    period: Optional[str], period_map: Optional[dict] = None
) -> Optional[str]:
    """Reject unknown period values, return the validated string (lower-cased).

    ``period_map`` is a mapping of accepted period keys (e.g. ``{"1m": 1, ...}``).
    When omitted, the default 1m/3m/6m/1y/5y map is used.
    """
    if period is None:
        return None
    if period_map is None:
        period_map = {"1m": 1, "3m": 3, "6m": 6, "1y": 12, "5y": 60}

    p = period.strip().lower()
    if p not in period_map:
        valid = ", ".join(period_map.keys())
        raise ValidationError(
            f"Invalid --period '{period}'. Valid options: {valid}."
        )
    return p


def validate_date_range(
    start: Optional[str], end: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    """Reject malformed, future, or out-of-order date inputs."""
    parsed_start = _parse_iso_date(start, "start date") if start else None
    parsed_end = _parse_iso_date(end, "end date") if end else None
    today = datetime.today()

    if parsed_start and parsed_start > today:
        raise ValidationError("Start date cannot be in the future.")
    if parsed_end and parsed_end > today:
        raise ValidationError("End date cannot be in the future.")
    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise ValidationError("Start date must be on or before end date.")

    return start, end


def validate_inputs(
    tickers: Iterable[str],
    start: Optional[str],
    end: Optional[str],
    period: Optional[str],
    period_map: Optional[dict] = None,
    ticker_re=None,
) -> tuple[list[str], Optional[str], Optional[str], Optional[str]]:
    """Run every pre-flight check. Returns the cleaned values on success.

    Raises ``ValidationError`` with a human-readable message on the first
    failed check, never reaching the network layer.
    """
    cleaned_tickers = validate_tickers(tickers, ticker_re=ticker_re)
    cleaned_period = validate_period(period, period_map=period_map)
    cleaned_start, cleaned_end = validate_date_range(start, end)
    return cleaned_tickers, cleaned_start, cleaned_end, cleaned_period
