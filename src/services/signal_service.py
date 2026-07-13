# Import standard library packaes.
from typing import cast

# Import third party packages.
import pandas as pd

# Import local packages.
from src.models.signal import Signal, SignalType


class SignalService:
    """
    Provides functionality for detecting trading signals and market levels.

    This service analyzes technical indicators to identify potential buy and
    sell opportunities based on indicator crossovers and threshold movements.
    """

    def serve_signals(
        self,
        data: pd.DataFrame,
        indicators: list[str],
        ticker: str,
    ) -> list[Signal]:
        """
        Detect trading signals based on active technical indicators.

        Supported signals:
            - RSI crossing above 30 or below 70.
            - MACD line crossing above or below the signal line.
            - EMA50 crossing EMA200 (golden/death cross).

        Args:
            data: OHLCV DataFrame containing calculated indicators.
            indicators: List of active indicator names.
            ticker: Stock ticker symbol associated with the signals.

        Returns:
            List of detected trading signals.
        """
        signals = []

        if data is None or data.empty:
            return signals

        signals.extend(self._detect_rsi_signals(data, indicators, ticker))
        signals.extend(self._detect_macd_signals(data, indicators, ticker))
        signals.extend(self._detect_ema_signals(data, indicators, ticker))
        return signals

    def detect_support_resistance(
        self,
        data: pd.DataFrame,
        window: int = 20,
        num_levels: int = 3,
    ) -> tuple[list[float], list[float]]:
        """
        Detect support and resistance levels using rolling extrema.

        Args:
            data: OHLCV DataFrame.
            window: Rolling window size used to identify extrema.
            num_levels: Number of support and resistance levels to return.

        Returns:
            Tuple containing support levels and resistance levels.
        """
        rolling_high = data["High"].rolling(window=window, center=True).max()
        rolling_low = data["Low"].rolling(window=window, center=True).min()
        resistance_mask = data["High"] == rolling_high
        support_mask = data["Low"] == rolling_low
        resistance_levels = sorted(
            data.loc[resistance_mask, "High"].nlargest(num_levels).tolist()
        )
        support_levels = sorted(
            data.loc[support_mask, "Low"].nsmallest(num_levels).tolist()
        )
        return support_levels, resistance_levels

    def _detect_rsi_signals(
        self,
        data: pd.DataFrame,
        indicators: list[str],
        ticker: str,
    ) -> list[Signal]:
        """
        Detect buy and sell signals based on RSI crossovers.
        """
        if "rsi" not in indicators or "RSI" not in data.columns:
            return []

        signals = []
        rsi = data["RSI"]
        buy = self._safe(rsi.shift(1).lt(30) & rsi.ge(30))
        sell = self._safe(rsi.shift(1).gt(70) & rsi.le(70))
        for date in data.index[buy]:
            close_price = cast(float, data.loc[date, "Close"])
            signal = Signal(
                ticker=ticker,
                date=date,
                signal_type=SignalType.BUY,
                price=float(close_price),
                reason="RSI crossed above oversold level",
            )
            signals.append(signal)

        for date in data.index[sell]:
            close_price = cast(float, data.loc[date, "Close"])
            signal = Signal(
                ticker=ticker,
                date=date,
                signal_type=SignalType.SELL,
                price=close_price,
                reason="RSI crossed below overbought level",
            )
            signals.append(signal)
        return signals

    def _detect_macd_signals(
        self,
        data: pd.DataFrame,
        indicators: list[str],
        ticker: str,
    ) -> list[Signal]:
        """
        Detect buy and sell signals based on MACD crossovers.
        """
        if "macd" not in indicators:
            return []

        if not all(column in data.columns for column in ("MACD", "MACD_Signal")):
            return []

        signals = []
        macd = data["MACD"]
        macd_signal = data["MACD_Signal"]
        buy = self._safe(macd.shift(1).lt(macd_signal.shift(1)) & macd.ge(macd_signal))
        sell = self._safe(macd.shift(1).gt(macd_signal.shift(1)) & macd.le(macd_signal))
        for date in data.index[buy]:
            close_price = cast(float, data.loc[date, "Close"])
            signal = Signal(
                ticker=ticker,
                date=date,
                signal_type=SignalType.BUY,
                price=close_price,
                reason="MACD crossed above signal line",
            )
            signals.append(signal)

        for date in data.index[sell]:
            close_price = cast(float, data.loc[date, "Close"])
            signal = Signal(
                ticker=ticker,
                date=date,
                signal_type=SignalType.SELL,
                price=close_price,
                reason="MACD crossed below signal line",
            )
            signals.append(signal)
        return signals

    def _detect_ema_signals(
        self,
        data: pd.DataFrame,
        indicators: list[str],
        ticker: str,
    ) -> list[Signal]:
        """
        Detect buy and sell signals based on EMA50/EMA200 crossovers.
        """
        if not all(indicator in indicators for indicator in ("ema50", "ema200")):
            return []

        if not all(column in data.columns for column in ("EMA50", "EMA200")):
            return []

        signals = []
        ema50 = data["EMA50"]
        ema200 = data["EMA200"]
        buy = self._safe(ema50.shift(1).lt(ema200.shift(1)) & ema50.ge(ema200))
        sell = self._safe(ema50.shift(1).gt(ema200.shift(1)) & ema50.le(ema200))
        for date in data.index[buy]:
            close_price = cast(float, data.loc[date, "Close"])
            signal = Signal(
                ticker=ticker,
                date=date,
                signal_type=SignalType.BUY,
                price=close_price,
                reason="EMA50 crossed above EMA200 (Golden Cross)",
            )
            signals.append(signal)

        for date in data.index[sell]:
            close_price = cast(float, data.loc[date, "Close"])
            signal = Signal(
                ticker=ticker,
                date=date,
                signal_type=SignalType.SELL,
                price=close_price,
                reason="EMA50 crossed below EMA200 (Death Cross)",
            )
            signals.append(signal)
        return signals

    @staticmethod
    def _safe(series: pd.Series) -> pd.Series:
        """
        Replace missing boolean values with False.

        Args:
            series: Boolean pandas Series.

        Returns:
            Boolean Series without missing values.
        """
        return series.fillna(False)
