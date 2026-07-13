# Import third party packages.
import pandas as pd
from pydantic import BaseModel, ConfigDict

# Import local packages.
from src.models.trade import Trade


class BacktestResult(BaseModel):
    """
    Represents the aggregated results produced by a backtesting run.

    Attributes:
        total_return: Total portfolio return generated during the backtest.
        buy_hold_return: Return of a passive buy-and-hold strategy over the same period.
        sharpe_ratio: Risk-adjusted return metric measuring return per unit of volatility.
        max_drawdown: Maximum observed portfolio decline from a peak to a trough.
        win_rate: Percentage of trades that were profitable.
        num_trades: Total number of completed round-trip trades.
        trades: List of all executed trades during the backtest.
        equity_curve: Portfolio value over time throughout the backtesting period.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    total_return: float
    buy_hold_return: float | None = None
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    num_trades: int | None = None
    trades: list[Trade]
    equity_curve: pd.DataFrame
