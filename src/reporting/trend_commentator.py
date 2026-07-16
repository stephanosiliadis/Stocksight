# Import third party packages.
import pandas as pd

# Import local packages.
from src.models.analysis_result import AnalysisResult


class TrendCommentator:
    """
    Builds a short plain-English summary of the most recent technical
    indicator readings for one ticker: RSI, Stochastic, MACD, EMA
    cross/trend, Bollinger Bands, and ATR/volatility.

    Each _*_comment method checks whether its indicator is both active and
    present in the data, and returns [] rather than raising if not --
    generate() just concatenates whatever comes back.
    """

    def __init__(self, result: AnalysisResult) -> None:
        self._data = result.indicators
        self._indicators = result.active_indicators

    def generate(self) -> str:
        """
        Build the commentary string.

        Returns:
            A short paragraph, or a fallback message if there isn't enough
            data or no active indicators to comment on.
        """
        if self._data is None or self._data.empty:
            return "No data available for commentary."

        last = self._data.iloc[-1]
        lines: list[str] = []

        lines.extend(self._rsi_comment(last))
        lines.extend(self._stochastic_comment(last))
        lines.extend(self._macd_comment(last))
        lines.extend(self._ema_cross_comment(last))
        lines.extend(self._price_vs_ema_comment(last))
        lines.extend(self._bollinger_comment(last))
        lines.extend(self._atr_comment(last))

        return (
            "  ".join(lines) if lines else "Insufficient indicator data for commentary."
        )

    def _rsi_comment(self, last: pd.Series) -> list[str]:
        """Comment on RSI overbought/oversold/neutral state."""
        if "rsi" not in self._indicators or "RSI" not in self._data.columns:
            return []

        rsi = last.get("RSI")
        if pd.isna(rsi):
            return []

        if rsi > 70:
            return [f"RSI is overbought at {rsi:.1f}, suggesting a potential pullback."]
        if rsi < 30:
            return [f"RSI is oversold at {rsi:.1f}, suggesting a potential bounce."]
        return [f"RSI is neutral at {rsi:.1f}."]

    def _stochastic_comment(self, last: pd.Series) -> list[str]:
        """Comment on Stochastic %K overbought/oversold state."""
        if "stochastic" not in self._indicators or "Stoch_K" not in self._data.columns:
            return []

        k_value = last.get("Stoch_K")
        if pd.isna(k_value):
            return []

        if k_value > 80:
            return [f"Stochastic %K ({k_value:.1f}) is overbought."]
        if k_value < 20:
            return [f"Stochastic %K ({k_value:.1f}) is oversold."]
        return []

    def _macd_comment(self, last: pd.Series) -> list[str]:
        """Comment on MACD vs signal line position and histogram momentum."""
        if "macd" not in self._indicators or "MACD" not in self._data.columns:
            return []

        macd = last.get("MACD")
        signal = last.get("MACD_Signal")
        histogram = last.get("MACD_Histogram")
        lines: list[str] = []

        if pd.notna(macd) and pd.notna(signal):
            direction = "above" if macd > signal else "below"
            sentiment = "bullish" if macd > signal else "bearish"
            lines.append(
                f"MACD ({macd:.2f}) is {direction} the signal line "
                f"({signal:.2f}), indicating {sentiment} momentum."
            )

        if pd.notna(histogram):
            lines.append(
                "Histogram is positive - momentum increasing."
                if histogram > 0
                else "Histogram is negative - momentum decreasing."
            )

        return lines

    def _ema_cross_comment(self, last: pd.Series) -> list[str]:
        """Comment on the EMA50/EMA200 Golden Cross / Death Cross state."""
        if not all(key in self._indicators for key in ("ema50", "ema200")):
            return []
        if not all(col in self._data.columns for col in ("EMA50", "EMA200")):
            return []

        ema50 = last.get("EMA50")
        ema200 = last.get("EMA200")
        if pd.isna(ema50) or pd.isna(ema200):
            return []

        if ema50 > ema200:
            return [
                f"Golden Cross active: EMA50 ({ema50:.2f}) is above EMA200 "
                f"({ema200:.2f}) - long-term bullish structure."
            ]
        return [
            f"Death Cross active: EMA50 ({ema50:.2f}) is below EMA200 "
            f"({ema200:.2f}) - long-term bearish structure."
        ]

    def _price_vs_ema_comment(self, last: pd.Series) -> list[str]:
        """Comment on price position relative to EMA50."""
        if "ema50" not in self._indicators or "EMA50" not in self._data.columns:
            return []

        ema50 = last.get("EMA50")
        close = last.get("Close")
        if pd.isna(ema50) or pd.isna(close):
            return []

        position = "above" if close > ema50 else "below"
        return [f"Price ({close:.2f}) is {position} EMA50 ({ema50:.2f})."]

    def _bollinger_comment(self, last: pd.Series) -> list[str]:
        """Comment on price position relative to the Bollinger Bands."""
        if (
            "bollinger" not in self._indicators
            or "Bollinger_Upper" not in self._data.columns
        ):
            return []

        close = last.get("Close")
        upper = last.get("Bollinger_Upper")
        lower = last.get("Bollinger_Lower")
        if pd.isna(close) or pd.isna(upper) or pd.isna(lower):
            return []

        if close > upper:
            return [
                "Price has broken above the upper Bollinger Band - potentially overbought."
            ]
        if close < lower:
            return [
                "Price has broken below the lower Bollinger Band - potentially oversold."
            ]
        return ["Price is trading within the Bollinger Bands."]

    def _atr_comment(self, last: pd.Series) -> list[str]:
        """Comment on ATR as a percentage of price (volatility label)."""
        if "atr" not in self._indicators or "ATR" not in self._data.columns:
            return []

        atr = last.get("ATR")
        close = last.get("Close")
        if pd.isna(atr) or pd.isna(close) or close <= 0:
            return []

        pct = (atr / close) * 100
        volatility = "high" if pct > 3 else ("moderate" if pct > 1.5 else "low")
        return [
            f"ATR is {atr:.2f} ({pct:.1f}% of price), indicating {volatility} volatility."
        ]
