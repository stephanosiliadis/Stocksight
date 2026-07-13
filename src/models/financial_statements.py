# Import third party packages.
from pydantic import BaseModel


class FinancialStatementRow(BaseModel):
    """
    Represents a single row of a financial statement.

    Attributes:
        label: Human-readable name of the financial metric.
        values: List of values corresponding to each reporting period.
    """

    label: str
    values: list[str]


class FinancialStatement(BaseModel):
    """
    Represents a complete financial statement containing multiple metrics
    across different reporting periods.

    Attributes:
        periods: List of reporting periods associated with the statement values.
        rows: List of financial metrics and their values for each period.
    """

    periods: list[str]
    rows: list[FinancialStatementRow]


class FinancialStatements(BaseModel):
    """
    Container for the three core financial statements of a company.

    Attributes:
        income_statement: Revenue, expenses, profitability, and earnings metrics.
        balance_sheet: Assets, liabilities, equity, and financial position metrics.
        cash_flow_statement: Cash inflows and outflows from operating,
            investing, and financing activities.
    """

    income_statement: FinancialStatement | None
    balance_sheet: FinancialStatement | None
    cash_flow_statement: FinancialStatement | None
