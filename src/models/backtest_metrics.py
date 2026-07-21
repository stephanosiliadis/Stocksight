from __future__ import annotations

from pydantic import BaseModel


class ExtendedBacktestMetrics(BaseModel):
    """
    Additional backtest performance metrics beyond BacktestResult's core
    four (total_return, sharpe_ratio, max_drawdown, win_rate).

    Deliberately a separate model rather than new fields bolted onto
    BacktestResult -- BacktestResult's exact shape is already depended on
    by PDFExporter, ExcelExporter, and backtest_panel.py, so widening it
    risks breaking all three. This model is produced from an existing
    BacktestResult by BacktestMetricsService and consumed independently.

    Attributes:
        sortino_ratio: Like the Sharpe ratio, but only downside volatility
            (the standard deviation of negative daily returns) penalizes
            the ratio, instead of overall volatility.
        profit_factor: Gross profit divided by gross loss (absolute value)
            across all trades. Capped at 999.0 when there are winning
            trades but zero losing trades, rather than dividing by zero
            or serializing an infinite value.
        expectancy: Expected profit/loss per trade in dollars:
            (win_rate * avg_winner) - (loss_rate * avg_loser).
        avg_winner: Average P&L of winning trades, in dollars (positive).
        avg_loser: Average loss magnitude of losing trades, in dollars,
            expressed as a positive number (e.g. 450.0, not -450.0).
        largest_winner: The single largest winning trade's P&L, in dollars.
        largest_loser: The single largest losing trade's loss magnitude,
            in dollars, expressed as a positive number.
    """

    sortino_ratio: float
    profit_factor: float
    expectancy: float
    avg_winner: float
    avg_loser: float
    largest_winner: float
    largest_loser: float
