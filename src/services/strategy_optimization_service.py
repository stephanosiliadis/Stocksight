from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from pandas_ta.momentum.rsi import rsi
from pandas_ta.overlap.ema import ema

from src.models.backtest_result import BacktestResult
from src.models.signal import Signal, SignalType
from src.services.backtest_service import BacktestService


@dataclass
class ParameterCombinationResult:
    """One tested parameter combination and the backtest it produced."""

    parameters: dict[str, float]
    backtest_result: BacktestResult


@dataclass
class OptimizationResult:
    """
    Full grid-search output for one ticker/strategy.

    Attributes:
        ticker: The ticker searched.
        all_results: Every parameter combination that produced a valid
            backtest (combinations with insufficient data to compute are
            silently skipped, not included as a failure).
    """

    ticker: str
    all_results: list[ParameterCombinationResult] = field(default_factory=list)

    @property
    def best(self) -> ParameterCombinationResult | None:
        """
        The combination with the highest total_return -- the same field
        BacktestResult already reports, not a new scoring formula.
        Returns None if every combination failed (e.g. not enough data
        for any of the tested periods).
        """
        if not self.all_results:
            return None
        return max(self.all_results, key=lambda r: r.backtest_result.total_return)


class StrategyOptimizationService:
    """
    Grid-searches RSI/EMA indicator parameters by generating signals for
    each combination and handing them to BacktestService for simulation
    and metrics.

    WHAT IS REUSED: trade execution and every performance metric (total
    return, Sharpe, max drawdown, win rate) come from the existing,
    UNMODIFIED BacktestService/BacktestEngine -- the part of a backtester
    that's genuinely risky to get subtly wrong. This service never
    recomputes any of that itself.

    WHAT IS NOT REUSED, AND WHY: the signal-generation step. SignalService
    hardcodes its RSI/EMA crossover periods and thresholds (14, 30/70,
    50/200) with no parameter to override them -- there's no "pass a
    custom RSI period" path anywhere in IndicatorService or SignalService
    today. Making those configurable would mean changing two services
    several other parts of the app already depend on, which is a bigger
    and riskier change than a Phase 9 add-on should make unilaterally. So
    _rsi_signals()/_ema_signals() below are a deliberately narrow,
    self-contained duplication of just the crossover LOGIC (mirroring
    SignalService's own detection rules exactly), parameterized -- not a
    duplication of the simulation or metrics logic, which stays reused.
    """

    def __init__(self, backtest_service: BacktestService | None = None) -> None:
        self._backtest_service = backtest_service or BacktestService()

    def optimize_rsi_strategy(
        self,
        ticker: str,
        data: pd.DataFrame,
        periods: list[int],
        oversold: float = 30.0,
        overbought: float = 70.0,
        initial_capital: float = 10_000.0,
    ) -> OptimizationResult:
        """
        Grid-search RSI period against a fixed oversold/overbought pair.

        Args:
            ticker: Ticker being optimized (passed through to Signal/Trade
                records, not used to fetch data -- `data` is the input).
            data: OHLCV data covering the in-sample window to search over.
            periods: RSI lengths to try, e.g. [7, 14, 21, 28].
            oversold: Buy-signal threshold (RSI crosses up through this).
            overbought: Sell-signal threshold (RSI crosses down through
                this).
            initial_capital: Starting capital for every backtest run.

        Returns:
            OptimizationResult with one entry per period that produced a
            valid backtest.
        """
        result = OptimizationResult(ticker=ticker)

        for period in periods:
            signals = self._rsi_signals(data, ticker, period, oversold, overbought)
            if signals is None:
                # RSI couldn't be computed at all for this period (not
                # enough data) -- skip, rather than letting
                # BacktestService produce a misleading 0-trade/0%-return
                # entry for a combination that was never actually usable.
                continue

            backtest = self._backtest_service.serve_backtest(
                ticker=ticker,
                data=data,
                signals=signals,
                initial_capital=initial_capital,
            )
            if backtest is not None:
                result.all_results.append(
                    ParameterCombinationResult(
                        parameters={
                            "rsi_period": period,
                            "oversold": oversold,
                            "overbought": overbought,
                        },
                        backtest_result=backtest,
                    )
                )

        return result

    def optimize_ema_strategy(
        self,
        ticker: str,
        data: pd.DataFrame,
        short_lengths: list[int],
        long_lengths: list[int],
        initial_capital: float = 10_000.0,
    ) -> OptimizationResult:
        """
        Grid-search short/long EMA length pairs for a golden/death cross
        strategy.

        Args:
            ticker: Ticker being optimized.
            data: OHLCV data covering the in-sample window to search over.
            short_lengths: Candidate short EMA lengths, e.g. [10, 20, 30].
            long_lengths: Candidate long EMA lengths, e.g. [100, 150, 200].
            initial_capital: Starting capital for every backtest run.

        Returns:
            OptimizationResult with one entry per (short, long) pair where
            short < long and the backtest produced a valid result. Pairs
            where short >= long are skipped -- not a meaningful
            "short-term vs long-term" cross.
        """
        result = OptimizationResult(ticker=ticker)

        for short_length in short_lengths:
            for long_length in long_lengths:
                if short_length >= long_length:
                    continue

                signals = self._ema_signals(data, ticker, short_length, long_length)
                if signals is None:
                    continue

                backtest = self._backtest_service.serve_backtest(
                    ticker=ticker,
                    data=data,
                    signals=signals,
                    initial_capital=initial_capital,
                )
                if backtest is not None:
                    result.all_results.append(
                        ParameterCombinationResult(
                            parameters={
                                "ema_short": short_length,
                                "ema_long": long_length,
                            },
                            backtest_result=backtest,
                        )
                    )

        return result

    def evaluate_out_of_sample(
        self,
        ticker: str,
        strategy_type: str,
        parameters: dict,
        out_of_sample_data: pd.DataFrame,
        initial_capital: float = 10_000.0,
    ) -> BacktestResult | None:
        """
        Re-run one specific parameter combination against a different
        (typically later) date range, to check whether an in-sample
        "best" result holds up out of sample or was just overfit to one
        narrow window -- see this phase's testing checklist.

        Args:
            ticker: Ticker being evaluated.
            strategy_type: "rsi" or "ema".
            parameters: A `.parameters` dict from a ParameterCombinationResult
                (e.g. {"rsi_period": 14, "oversold": 30.0, "overbought": 70.0}
                or {"ema_short": 20, "ema_long": 100}).
            out_of_sample_data: OHLCV data for the validation window --
                should NOT overlap the window `parameters` was found on.
            initial_capital: Starting capital for the validation backtest.

        Returns:
            BacktestResult for this combination on the new data, or None
            if there wasn't enough data to compute it.

        Raises:
            ValueError: If strategy_type isn't "rsi" or "ema".
        """
        if strategy_type == "rsi":
            signals = self._rsi_signals(
                out_of_sample_data,
                ticker,
                int(parameters["rsi_period"]),
                float(parameters.get("oversold", 30.0)),
                float(parameters.get("overbought", 70.0)),
            )
        elif strategy_type == "ema":
            signals = self._ema_signals(
                out_of_sample_data,
                ticker,
                int(parameters["ema_short"]),
                int(parameters["ema_long"]),
            )
        else:
            raise ValueError(f"Unknown strategy_type: {strategy_type!r}")

        if signals is None:
            # Not enough out-of-sample data to even compute the
            # indicator -- nothing to validate.
            return None

        return self._backtest_service.serve_backtest(
            ticker=ticker,
            data=out_of_sample_data,
            signals=signals,
            initial_capital=initial_capital,
        )

    def _rsi_signals(
        self,
        data: pd.DataFrame,
        ticker: str,
        period: int,
        oversold: float,
        overbought: float,
    ) -> list[Signal] | None:
        """
        Mirrors SignalService._detect_rsi_signals's exact crossing rule
        (buy when RSI crosses up through `oversold`, sell when it crosses
        down through `overbought`), parameterized by period/thresholds.

        Returns:
            List of signals (possibly empty, if RSI computed fine but
            simply never crossed either threshold), or None if RSI
            couldn't be computed at all for this period (not enough
            data) -- callers should skip None, not treat it as "zero
            signals found".
        """
        rsi_values = rsi(data["Close"], length=period)
        if rsi_values is None:
            # pandas_ta returns None (not a NaN Series) when there's less
            # data than `period` -- same behavior IndicatorService already
            # guards against elsewhere in this app.
            return None

        buy_mask = ((rsi_values.shift(1) < oversold) & (rsi_values >= oversold)).fillna(
            False
        )
        sell_mask = (
            (rsi_values.shift(1) > overbought) & (rsi_values <= overbought)
        ).fillna(False)

        signals: list[Signal] = []
        for dt in data.index[buy_mask]:
            signals.append(
                Signal(
                    ticker=ticker,
                    date=dt,
                    signal_type=SignalType.BUY,
                    price=float(data.loc[dt, "Close"]),
                    reason=f"RSI({period}) crossed above {oversold:g}",
                )
            )
        for dt in data.index[sell_mask]:
            signals.append(
                Signal(
                    ticker=ticker,
                    date=dt,
                    signal_type=SignalType.SELL,
                    price=float(data.loc[dt, "Close"]),
                    reason=f"RSI({period}) crossed below {overbought:g}",
                )
            )

        return signals

    def _ema_signals(
        self,
        data: pd.DataFrame,
        ticker: str,
        short_length: int,
        long_length: int,
    ) -> list[Signal] | None:
        """
        Mirrors SignalService._detect_ema_signals's exact crossing rule
        (golden/death cross), parameterized by the two EMA lengths.

        Returns:
            List of signals (possibly empty), or None if either EMA
            couldn't be computed at all (not enough data) -- callers
            should skip None, not treat it as "zero signals found".
        """
        ema_short = ema(data["Close"], length=short_length)
        ema_long = ema(data["Close"], length=long_length)
        if ema_short is None or ema_long is None:
            return None

        buy_mask = (
            (ema_short.shift(1) < ema_long.shift(1)) & (ema_short >= ema_long)
        ).fillna(False)
        sell_mask = (
            (ema_short.shift(1) > ema_long.shift(1)) & (ema_short <= ema_long)
        ).fillna(False)

        signals: list[Signal] = []
        for dt in data.index[buy_mask]:
            signals.append(
                Signal(
                    ticker=ticker,
                    date=dt,
                    signal_type=SignalType.BUY,
                    price=float(data.loc[dt, "Close"]),
                    reason=f"EMA{short_length} crossed above EMA{long_length}",
                )
            )
        for dt in data.index[sell_mask]:
            signals.append(
                Signal(
                    ticker=ticker,
                    date=dt,
                    signal_type=SignalType.SELL,
                    price=float(data.loc[dt, "Close"]),
                    reason=f"EMA{short_length} crossed below EMA{long_length}",
                )
            )

        return signals
