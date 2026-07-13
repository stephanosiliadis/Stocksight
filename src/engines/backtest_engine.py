# Import standard library packages.
from datetime import datetime

# Import third party packages.
import pandas as pd

# Import local packages.
from src.models.trade import Trade


class BacktestEngine:
    """
    Executes the trading simulation for a signal-driven strategy.

    This class is responsible only for portfolio execution. It manages cash,
    positions, trade execution, and equity tracking. It does not calculate
    performance metrics or create the final backtest result.
    """

    def __init__(
        self,
        ticker: str,
        initial_capital: float,
    ) -> None:
        """
        Initialize the backtesting engine.

        Args:
            ticker: Stock ticker symbol being tested.
            initial_capital: Starting portfolio capital.
        """
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.cash: float = initial_capital
        self.shares: float = 0.0
        self.entry_price: float | None = None
        self.entry_date: datetime | None = None
        self.trades: list[Trade] = []
        self.equity_dates: list[pd.Timestamp] = []
        self.equity_values: list[float] = []

    def run(
        self,
        data: pd.DataFrame,
        signals: pd.DataFrame,
    ) -> tuple[list[Trade], pd.DataFrame]:
        """
        Execute the backtest simulation.

        Args:
            data: Historical OHLCV market data indexed by date.
            signals: DataFrame containing generated Buy and Sell signals.

        Returns:
            A tuple containing:
                - List of completed trades.
                - Portfolio equity curve over time.
        """
        for raw_date, row in data.iterrows():
            date = pd.Timestamp(str(raw_date))
            close = row.get("Close")

            if close is None or pd.isna(close) or close <= 0:
                continue

            close = float(close)
            signal: pd.Series | None = None
            if date in signals.index:
                raw_signal = signals.loc[date]
                if isinstance(raw_signal, pd.Series):
                    signal = raw_signal

            if self._is_buy_signal(signal):
                self._buy(
                    date,
                    close,
                )

            elif self._is_sell_signal(signal):
                self._sell(
                    date,
                    close,
                )

            self._record_equity(
                date,
                close,
            )

        return (
            self.trades,
            self._create_equity_curve(),
        )

    def _buy(
        self,
        date: pd.Timestamp,
        price: float,
    ) -> None:
        """
        Open a long position using all available cash.

        Args:
            date: Date of the buy transaction.
            price: Closing price at which the position is opened.
        """
        if self.cash <= 0 or self.shares > 0:
            return

        self.shares = self.cash / price
        self.entry_price = price
        self.entry_date = date.to_pydatetime()
        self.cash = 0.0

    def _sell(
        self,
        date: pd.Timestamp,
        price: float,
    ) -> None:
        """
        Close the current position and record the completed trade.

        Args:
            date: Date of the sell transaction.
            price: Closing price at which the position is closed.
        """
        if self.shares <= 0 or self.entry_price is None or self.entry_date is None:
            return

        proceeds = self.shares * price
        cost = self.shares * self.entry_price
        pnl = proceeds - cost
        trade = Trade(
            ticker=self.ticker,
            entry_date=self.entry_date,
            exit_date=date.to_pydatetime(),
            entry_price=self.entry_price,
            exit_price=price,
            pnl=float(pnl),
            return_pct=float((pnl / cost) * 100 if cost else 0.0),
        )

        self.trades.append(trade)
        self.cash = proceeds
        self.shares = 0.0
        self.entry_price = None
        self.entry_date = None

    def _record_equity(
        self,
        date: pd.Timestamp,
        price: float,
    ) -> None:
        """
        Record current portfolio value.

        Args:
            date: Current market date.
            price: Current closing price used for valuation.
        """
        value = self.cash + self.shares * price
        self.equity_dates.append(date)
        self.equity_values.append(float(value))

    def _create_equity_curve(self) -> pd.DataFrame:
        """
        Create a DataFrame representing portfolio value over time.

        Returns:
            DataFrame with portfolio value indexed by date.
        """
        return pd.DataFrame(
            {
                "Portfolio": self.equity_values,
            },
            index=self.equity_dates,
        )

    @staticmethod
    def _is_buy_signal(
        signal: pd.Series | None,
    ) -> bool:
        """
        Determine whether a buy signal exists.

        Args:
            signal: Signal row containing Buy/Sell columns.

        Returns:
            True if a valid buy signal is present.
        """
        return signal is not None and pd.notna(signal.get("Buy"))

    @staticmethod
    def _is_sell_signal(
        signal: pd.Series | None,
    ) -> bool:
        """
        Determine whether a sell signal exists.

        Args:
            signal: Signal row containing Buy/Sell columns.

        Returns:
            True if a valid sell signal is present.
        """
        return signal is not None and pd.notna(signal.get("Sell"))
