# Import standard library packages.
from datetime import date

# Import third party packages.
from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    """
    Request model containing all configuration options for a stock analysis run.

    Attributes:
        tickers: List of stock ticker symbols to analyze.
        start_date: Optional start date for a custom analysis period.
        end_date: Optional end date for a custom analysis period.
        period: Optional predefined period string (e.g. "1mo", "1y", "5y").
        indicators: List of technical indicators to calculate and display.
        include_fundamentals: Whether to include fundamental company metrics.
        include_statements: Whether to include financial statements data.
        compare: Whether to perform comparative analysis between multiple tickers.
        backtest: Whether to run a backtesting simulation.
        initial_capital: Initial capital used for backtesting.
        export_pdf: Whether to export the results as a PDF report.
        export_excel: Whether to export the results as an Excel file.
    """

    tickers: list[str]
    start_date: date | None = None
    end_date: date | None = None
    period: str | None = None
    indicators: list[str]
    include_fundamentals: bool = False
    include_statements: bool = False
    compare: bool = False
    backtest: bool = False
    initial_capital: float = 10_000.0
    export_pdf: bool = False
    export_excel: bool = False
