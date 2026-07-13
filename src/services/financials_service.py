# Import third party packages.
import pandas as pd
import yfinance as yf

# Import local packages.
from src.models.financial_statements import (
    FinancialStatement,
    FinancialStatementRow,
    FinancialStatements,
)


class FinancialsService:
    """
    Provides functionality for retrieving and processing company financial
    statements.

    This service fetches income statements, balance sheets, and cash flow
    statements from Yahoo Finance and converts them into structured Pydantic
    models for analysis and visualization.
    """

    _INCOME_KEYS = [
        "Total Revenue",
        "Cost Of Revenue",
        "Gross Profit",
        "Operating Income",
        "Ebitda",
        "Pretax Income",
        "Tax Provision",
        "Net Income",
        "Basic EPS",
        "Diluted EPS",
    ]

    _BALANCE_KEYS = [
        "Cash And Cash Equivalents",
        "Total Current Assets",
        "Total Assets",
        "Total Current Liabilities",
        "Total Liabilities Net Minority Interest",
        "Stockholders Equity",
        "Total Debt",
        "Long Term Debt",
        "Retained Earnings",
        "Working Capital",
    ]

    _CASHFLOW_KEYS = [
        "Operating Cash Flow",
        "Capital Expenditure",
        "Free Cash Flow",
        "Investing Cash Flow",
        "Financing Cash Flow",
        "Issuance Of Debt",
        "Repayment Of Debt",
        "Repurchase Of Capital Stock",
        "Cash Dividends Paid",
        "Changes In Cash",
    ]

    _LABEL_MAP = {
        "Total Liabilities Net Minority Interest": "Total Liabilities",
        "Cash And Cash Equivalents": "Cash & Equivalents",
        "Issuance Of Debt": "Debt Issued",
        "Repayment Of Debt": "Debt Repaid",
        "Repurchase Of Capital Stock": "Share Buybacks",
        "Cash Dividends Paid": "Dividends Paid",
        "Ebitda": "EBITDA",
    }

    def serve_financial_statements(
        self,
        ticker: str,
        quarterly: bool = False,
    ) -> FinancialStatements | None:
        """
        Fetch and process financial statements for a stock ticker.

        Args:
            ticker: Stock ticker symbol.
            quarterly: Whether to fetch quarterly statements instead of annual
                statements.

        Returns:
            FinancialStatements containing income statement, balance sheet,
            and cash flow statement data, or None if unavailable.
        """
        try:
            stock = yf.Ticker(ticker)
            income = stock.quarterly_income_stmt if quarterly else stock.income_stmt
            balance = (
                stock.quarterly_balance_sheet if quarterly else stock.balance_sheet
            )
            cash_flow = stock.quarterly_cashflow if quarterly else stock.cashflow
            return FinancialStatements(
                income_statement=self._extract_statement(
                    income,
                    self._INCOME_KEYS,
                ),
                balance_sheet=self._extract_statement(
                    balance,
                    self._BALANCE_KEYS,
                ),
                cash_flow_statement=self._extract_statement(
                    cash_flow,
                    self._CASHFLOW_KEYS,
                ),
            )

        except Exception:
            return None

    def _extract_statement(
        self,
        data: pd.DataFrame,
        keys: list[str],
        max_periods: int = 3,
    ) -> FinancialStatement | None:
        """
        Extract relevant rows from a financial statement DataFrame.

        Args:
            data: Yahoo Finance financial statement DataFrame.
            keys: Financial metrics to extract.
            max_periods: Maximum number of reporting periods to include.

        Returns:
            FinancialStatement model or None if no data is available.
        """
        if data is None or data.empty:
            return None

        columns = data.columns[:max_periods]

        periods = []

        for column in columns:
            try:
                periods.append(pd.Timestamp(column).strftime("%Y"))
            except Exception:
                periods.append(str(column)[:4])

        rows = []
        for key in keys:
            match = next(
                (item for item in data.index if item.lower() == key.lower()),
                None,
            )
            if match is None:
                continue

            label = self._LABEL_MAP.get(match, match)
            values = [self._format_value(data.loc[match, column]) for column in columns]
            if label is not None:
                row = FinancialStatementRow(
                    label=label,
                    values=values,
                )

                rows.append(row)

        if not rows:
            return None

        return FinancialStatement(
            periods=periods,
            rows=rows,
        )

    @staticmethod
    def _format_value(value) -> str:
        """
        Format a financial value into a human-readable representation.

        Args:
            value: Numeric financial value.

        Returns:
            Formatted string representation.
        """
        if value is None or pd.isna(value):
            return "N/A"

        try:
            number = float(value)
            sign = "-" if number < 0 else ""
            absolute = abs(number)
            if absolute >= 1e12:
                return f"{sign}${absolute / 1e12:.2f}T"

            if absolute >= 1e9:
                return f"{sign}${absolute / 1e9:.2f}B"

            if absolute >= 1e6:
                return f"{sign}${absolute / 1e6:.2f}M"

            if absolute >= 1e3:
                return f"{sign}${absolute / 1e3:.2f}K"

            return f"{sign}${absolute:.2f}"

        except (TypeError, ValueError):
            return str(value)
