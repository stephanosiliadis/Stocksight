from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from src.models.earnings import EarningsEvent
from src.services.fundamentals_service import FundamentalsService


class EarningsService:
    """
    Converts the raw earnings calendar data FundamentalsService already
    fetches into typed EarningsEvent models.

    This deliberately does NOT re-implement the yfinance call:
    FundamentalsService.serve_earnings_dates() already fetches
    yf.Ticker(ticker).calendar, so this service's only job is to reshape
    whatever that returns.

    Because `.calendar` is yfinance's forward-looking earnings/dividend
    estimate endpoint (not a historical earnings-with-actuals feed), every
    EarningsEvent produced here has is_estimate=True and eps_actual=None.
    Getting reported actuals would require a different yfinance call,
    which is out of scope for a service that strictly reuses
    FundamentalsService's existing method.
    """

    def __init__(self, fundamentals_service: FundamentalsService | None = None) -> None:
        self._fundamentals_service = fundamentals_service or FundamentalsService()

    def serve_earnings(self, ticker: str) -> list[EarningsEvent]:
        """
        Fetch and reshape upcoming earnings dates for a ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            List of EarningsEvent, or an empty list (never raises) if no
            calendar data is available.
        """
        raw_calendar = self._fundamentals_service.serve_earnings_dates(ticker)
        if raw_calendar is None:
            return []

        calendar = self._normalize_to_dict(raw_calendar)
        if not calendar:
            return []

        earnings_dates = self._extract_earnings_dates(calendar)
        if not earnings_dates:
            return []

        eps_estimate = self._safe_float(calendar.get("Earnings Average"))

        return [
            EarningsEvent(
                date=earnings_date,
                is_estimate=True,
                eps_estimate=eps_estimate,
                eps_actual=None,
            )
            for earnings_date in earnings_dates
        ]

    def _normalize_to_dict(self, raw: pd.DataFrame | dict) -> dict:
        """
        Normalize either shape FundamentalsService.serve_earnings_dates
        can return (dict, or an older-style single-column DataFrame) into
        a plain dict of field name -> value.
        """
        if isinstance(raw, dict):
            return raw

        if isinstance(raw, pd.DataFrame):
            try:
                return raw.iloc[:, 0].to_dict()
            except Exception:
                return {}

        return {}

    def _extract_earnings_dates(self, calendar: dict) -> list[date]:
        """Pull the "Earnings Date" entry out, normalizing to a list of dates."""
        raw_dates = calendar.get("Earnings Date")
        if raw_dates is None:
            return []

        if not isinstance(raw_dates, (list, tuple)):
            raw_dates = [raw_dates]

        parsed_dates = []
        for value in raw_dates:
            parsed = self._to_date(value)
            if parsed is not None:
                parsed_dates.append(parsed)

        return parsed_dates

    @staticmethod
    def _to_date(value) -> date | None:
        """Best-effort conversion of a yfinance calendar date value to date."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return pd.Timestamp(value).date()
        except Exception:
            return None

    @staticmethod
    def _safe_float(value) -> float | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
