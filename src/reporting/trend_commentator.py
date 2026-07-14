from __future__ import annotations

import pandas as pd

from src.models.analysis_result import AnalysisResult


class TrendCommentator:
    """
    Generates plain-English technical analysis commentary
    from an AnalysisResult.
    """

    def __init__(self, result: AnalysisResult) -> None:
        self._result = result
        self._data = result.indicators
        self._indicators = result.active_indicators

    def generate(self) -> str:
        """
        Generate a technical summary for the latest data point.

        Returns:
            Human-readable technical commentary.
        """
        if self._data is None or self._data.empty:
            return "No data available for commentary."

        lines: list[str] = []

        self._add_rsi_comment(lines)
        self._add_stochastic_comment(lines)
        self._add_macd_comment(lines)
        self._add_ema_comment(lines)
        self._add_bollinger_comment(lines)
        self._add_atr_comment(lines)

        return (
            " ".join(lines) if lines else "Insufficient indicator data for commentary."
        )

    def _last_value(self, column: str) -> float | None:
        """
        Safely retrieve the latest indicator value.
        """
        if column not in self._data.columns:
            return None

        value = self._data[column].iloc[-1]

        if pd.isna(value):
            return None

        return float(value)

    def _add_rsi_comment(self, lines: list[str]) -> None:
        if "rsi" not in self._indicators:
            return

        rsi = self._last_value("RSI")

        if rsi is None:
            return

        if rsi > 70:
            lines.append(
                f"RSI is overbought at {rsi:.1f}, suggesting a possible pullback."
            )
        elif rsi < 30:
            lines.append(
                f"RSI is oversold at {rsi:.1f}, suggesting a possible rebound."
            )
        else:
            lines.append(f"RSI is neutral at {rsi:.1f}.")

    def _add_stochastic_comment(self, lines: list[str]) -> None:
        if "stochastic" not in self._indicators:
            return

        value = self._last_value("Stoch_K")

        if value is None:
            return

        if value > 80:
            lines.append(f"Stochastic %K is overbought at {value:.1f}.")
        elif value < 20:
            lines.append(f"Stochastic %K is oversold at {value:.1f}.")

    def _add_macd_comment(self, lines: list[str]) -> None:
        if "macd" not in self._indicators:
            return

        macd = self._last_value("MACD")
        signal = self._last_value("MACD_Signal")
        histogram = self._last_value("MACD_Histogram")

        if macd is not None and signal is not None:
            direction = "above" if macd > signal else "below"
            sentiment = "bullish" if macd > signal else "bearish"

            lines.append(
                f"MACD ({macd:.2f}) is {direction} the signal line "
                f"({signal:.2f}), indicating {sentiment} momentum."
            )

        if histogram is not None:
            if histogram > 0:
                lines.append(
                    "MACD histogram is positive, indicating increasing momentum."
                )
            else:
                lines.append(
                    "MACD histogram is negative, indicating weakening momentum."
                )

    def _add_ema_comment(self, lines: list[str]) -> None:
        if not {"ema50", "ema200"}.issubset(self._indicators):
            return

        ema50 = self._last_value("EMA50")
        ema200 = self._last_value("EMA200")

        if ema50 is None or ema200 is None:
            return

        if ema50 > ema200:
            lines.append(
                f"EMA50 ({ema50:.2f}) is above EMA200 ({ema200:.2f}), "
                "showing a long-term bullish structure."
            )
        else:
            lines.append(
                f"EMA50 ({ema50:.2f}) is below EMA200 ({ema200:.2f}), "
                "showing a long-term bearish structure."
            )

    def _add_bollinger_comment(self, lines: list[str]) -> None:
        if "bollinger" not in self._indicators:
            return

        close = self._last_value("Close")
        upper = self._last_value("Bollinger_Upper")
        lower = self._last_value("Bollinger_Lower")

        if close is None or upper is None or lower is None:
            return

        if close > upper:
            lines.append(
                "Price is above the upper Bollinger Band, suggesting possible overextension."
            )
        elif close < lower:
            lines.append(
                "Price is below the lower Bollinger Band, suggesting possible oversold conditions."
            )
        else:
            lines.append("Price is trading within the Bollinger Bands.")

    def _add_atr_comment(self, lines: list[str]) -> None:
        if "atr" not in self._indicators:
            return

        atr = self._last_value("ATR")
        close = self._last_value("Close")

        if atr is None or close is None or close == 0:
            return

        percentage = (atr / close) * 100

        if percentage > 3:
            volatility = "high"
        elif percentage > 1.5:
            volatility = "moderate"
        else:
            volatility = "low"

        lines.append(
            f"ATR is {atr:.2f} ({percentage:.1f}% of price), indicating {volatility} volatility."
        )
