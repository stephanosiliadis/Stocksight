from __future__ import annotations

import numpy as np
import pandas as pd

from src.models.backtest_metrics import ExtendedBacktestMetrics
from src.models.backtest_result import BacktestResult
from src.models.trade import Trade


class BacktestMetricsService:
    """
    Derives extended backtest metrics (Sortino, profit factor, expectancy,
    per-trade attribution) purely from an existing BacktestResult.

    Everything here is computed from ``backtest.trades`` and
    ``backtest.equity_curve`` only -- this service never touches raw price
    data. Every metric degrades to a sensible default (0.0, or a capped
    sentinel for profit_factor) instead of raising, so callers don't need
    to special-case zero-trade, all-winning, or all-losing backtests.
    """

    # Sentinel used for profit_factor when there are winning trades but
    # zero losing trades. Deliberately not float('inf'): infinities are
    # awkward to serialize (JSON, Excel) and easy to forget to guard
    # against downstream, whereas a large finite number behaves like any
    # other float everywhere it's used.
    UNBOUNDED_PROFIT_FACTOR = 999.0

    def calculate(self, backtest: BacktestResult) -> ExtendedBacktestMetrics:
        """
        Compute extended performance metrics for a completed backtest.

        Args:
            backtest: The BacktestResult to derive metrics from.

        Returns:
            ExtendedBacktestMetrics with every field populated, even for
            edge-case backtests (zero trades, all winners, all losers).
        """
        trades = backtest.trades or []
        winners = self._winners(trades)
        losers = self._losers(trades)

        return ExtendedBacktestMetrics(
            sortino_ratio=self._sortino_ratio(backtest.equity_curve),
            profit_factor=self._profit_factor(trades),
            expectancy=self._expectancy(trades),
            avg_winner=self._average_pnl(winners),
            avg_loser=self._average_loss_magnitude(losers),
            largest_winner=self._largest_winner(trades),
            largest_loser=self._largest_loser_magnitude(trades),
        )

    def serve_trade_attribution(
        self,
        backtest: BacktestResult,
    ) -> dict[str, Trade | None]:
        """
        Surface the single biggest winning and losing trade.

        Trade does not currently retain a link back to the Signal.reason
        that triggered its entry, so this can't group winners/losers by
        entry condition -- that grouping was noted as an optional bonus
        in the roadmap, not a requirement. What this does answer is
        "what was this backtest's best and worst trade, and by how much",
        directly from the trade log.

        Args:
            backtest: The BacktestResult to inspect.

        Returns:
            {"best_trade": Trade | None, "worst_trade": Trade | None}.
            Both are None if there were no trades.
        """
        trades = backtest.trades or []

        if not trades:
            return {"best_trade": None, "worst_trade": None}

        best_trade = max(trades, key=lambda trade: trade.pnl)
        worst_trade = min(trades, key=lambda trade: trade.pnl)

        return {"best_trade": best_trade, "worst_trade": worst_trade}

    # ------------------------------------------------------------------
    # Trade classification helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _winners(trades: list[Trade]) -> list[Trade]:
        """Trades with strictly positive P&L."""
        return [trade for trade in trades if trade.pnl > 0]

    @staticmethod
    def _losers(trades: list[Trade]) -> list[Trade]:
        """Trades with strictly negative P&L."""
        return [trade for trade in trades if trade.pnl < 0]

    @staticmethod
    def _average_pnl(trades: list[Trade]) -> float:
        """Average P&L across a list of trades, or 0.0 if empty."""
        if not trades:
            return 0.0
        return float(sum(trade.pnl for trade in trades) / len(trades))

    @staticmethod
    def _average_loss_magnitude(losers: list[Trade]) -> float:
        """Average loss size as a positive number, or 0.0 if no losers."""
        if not losers:
            return 0.0
        return float(sum(abs(trade.pnl) for trade in losers) / len(losers))

    @staticmethod
    def _largest_winner(trades: list[Trade]) -> float:
        """Largest single winning trade's P&L, or 0.0 if no winners."""
        winner_pnls = [trade.pnl for trade in trades if trade.pnl > 0]
        return float(max(winner_pnls)) if winner_pnls else 0.0

    @staticmethod
    def _largest_loser_magnitude(trades: list[Trade]) -> float:
        """Largest single losing trade's loss size (positive), or 0.0."""
        loser_pnls = [trade.pnl for trade in trades if trade.pnl < 0]
        return float(abs(min(loser_pnls))) if loser_pnls else 0.0

    # ------------------------------------------------------------------
    # Formulas
    # ------------------------------------------------------------------

    def _profit_factor(self, trades: list[Trade]) -> float:
        """
        Gross profit / gross loss (absolute value) across all trades.

        Returns 0.0 for zero trades or zero winning trades (no profit to
        speak of). Returns UNBOUNDED_PROFIT_FACTOR when there is at least
        one winning trade but zero losing trades, instead of dividing by
        zero.
        """
        gross_profit = sum(trade.pnl for trade in trades if trade.pnl > 0)
        gross_loss = sum(abs(trade.pnl) for trade in trades if trade.pnl < 0)

        if gross_loss == 0:
            return self.UNBOUNDED_PROFIT_FACTOR if gross_profit > 0 else 0.0

        return float(gross_profit / gross_loss)

    def _expectancy(self, trades: list[Trade]) -> float:
        """
        (win_rate * avg_winner) - (loss_rate * avg_loser), where avg_loser
        is a positive loss magnitude -- so expectancy is a signed dollar
        figure: positive means the strategy is profitable per trade on
        average, negative means it loses money per trade on average.
        """
        if not trades:
            return 0.0

        total_trades = len(trades)
        winners = self._winners(trades)
        losers = self._losers(trades)

        win_rate = len(winners) / total_trades
        loss_rate = len(losers) / total_trades

        avg_winner = self._average_pnl(winners)
        avg_loser = self._average_loss_magnitude(losers)

        return float((win_rate * avg_winner) - (loss_rate * avg_loser))

    def _sortino_ratio(self, equity_curve: pd.DataFrame) -> float:
        """
        Like Sharpe, but only downside volatility (std of negative daily
        returns) penalizes the ratio. Matches BacktestService's existing
        Sharpe assumptions: 252 trading days/year, 0% risk-free rate.

        Returns 0.0 if there's no equity curve, no returns, or no
        downside returns at all (e.g. a flat or always-up equity curve),
        rather than dividing by a zero or NaN standard deviation.
        """
        if (
            equity_curve is None
            or equity_curve.empty
            or "Portfolio" not in equity_curve.columns
        ):
            return 0.0

        daily_returns = equity_curve["Portfolio"].pct_change().dropna()
        if daily_returns.empty:
            return 0.0

        downside_returns = daily_returns[daily_returns < 0]
        downside_std = downside_returns.std()

        if not downside_std or pd.isna(downside_std) or downside_std == 0:
            return 0.0

        return float((daily_returns.mean() / downside_std) * np.sqrt(252))
