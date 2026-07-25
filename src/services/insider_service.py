from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import yfinance as yf

from src.models.insider_transaction import InsiderTransaction


class InsiderService:
    """
    Provides functionality for retrieving insider buy/sell activity.
    """

    def serve_transactions(self, ticker: str) -> list[InsiderTransaction]:
        """
        Fetch insider transactions for a stock ticker.

        Args:
            ticker: Stock ticker symbol.

        Returns:
            List of InsiderTransaction, possibly empty. Never raises --
            any fetch or parsing failure results in an empty list.
        """
        try:
            data = yf.Ticker(ticker).insider_transactions
        except Exception:
            return []

        if not isinstance(data, pd.DataFrame) or data.empty:
            return []

        transactions: list[InsiderTransaction] = []
        for _, row in data.iterrows():
            transaction = self._row_to_transaction(row)
            if transaction is not None:
                transactions.append(transaction)

        return transactions

    def _row_to_transaction(self, row: pd.Series) -> InsiderTransaction | None:
        """
        Convert a single insider_transactions row into a typed model.

        Column names in yfinance's insider_transactions DataFrame aren't
        perfectly stable across versions, so this reads defensively and
        skips (returns None for) any row it can't make sense of, rather
        than letting one malformed row abort the whole ticker.
        """
        try:
            parsed_date = self._to_date(row.get("Start Date"))
            if parsed_date is None:
                return None

            return InsiderTransaction(
                insider_name=str(row.get("Insider") or "Unknown"),
                date=parsed_date,
                transaction_type=str(
                    row.get("Transaction") or row.get("Text") or "Unknown"
                ),
                shares=self._safe_int(row.get("Shares")),
                value=self._safe_float(row.get("Value")),
            )
        except Exception:
            return None

    @staticmethod
    def _to_date(value) -> date | None:
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
    def _safe_int(value) -> int:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_float(value) -> float | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
