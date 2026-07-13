# Import third party packages.
from pandas import DataFrame
from pandas_ta.momentum.macd import macd
from pandas_ta.momentum.rsi import rsi
from pandas_ta.momentum.stoch import stoch
from pandas_ta.overlap.ema import ema
from pandas_ta.volatility.atr import atr
from pandas_ta.volatility.bbands import bbands


class IndicatorService:
    """
    Provides technical analysis functionality for stock market data.

    This service calculates technical indicators from OHLCV market data and
    appends the resulting values as additional columns to the input DataFrame.
    """

    _ALL_INDICATORS = [
        "bollinger",
        "rsi",
        "macd",
        "ema20",
        "ema50",
        "ema200",
        "atr",
        "stochastic",
    ]

    def __init__(self) -> None:
        self._INDICATORS = {
            "bollinger": self._calculate_bollinger,
            "rsi": self._calculate_rsi,
            "macd": self._calculate_macd,
            "ema20": self._calculate_ema20,
            "ema50": self._calculate_ema50,
            "ema200": self._calculate_ema200,
            "atr": self._calculate_atr,
            "stochastic": self._calculate_stochastic,
        }

    def serve_indicators(
        self, data: DataFrame, indicators: list[str] | None = None
    ) -> DataFrame | None:
        """
        Calculate selected technical indicators.

        Args:
            data: OHLCV stock market data.
            indicators: List of indicators to calculate. If None, calculates
                all available indicators.

        Returns:
            DataFrame with indicator columns appended, or None if input is invalid.
        """
        if data is None or data.empty:
            return None

        if indicators is None:
            indicators = self._ALL_INDICATORS

        for indicator in indicators:
            calculator = self._INDICATORS.get(indicator)

            if calculator:
                try:
                    data = calculator(data)
                except Exception:
                    pass

        return data

    def _calculate_rsi(self, data: DataFrame) -> DataFrame:
        """
        Calculate Relative Strength Index (RSI).

        Args:
            data: OHLCV DataFrame.

        Returns:
            DataFrame with RSI column added.
        """
        data["RSI"] = rsi(data["Close"], length=14)
        return data

    def _calculate_macd(self, data: DataFrame) -> DataFrame:
        """
        Calculate Moving Average Convergence Divergence (MACD).

        Args:
            data: OHLCV DataFrame.

        Returns:
            DataFrame with MACD columns added.
        """
        result = macd(data["Close"])

        if result is not None:
            data["MACD"] = result.iloc[:, 0]
            data["MACD_Histogram"] = result.iloc[:, 1]
            data["MACD_Signal"] = result.iloc[:, 2]

        return data

    def _calculate_ema20(self, data: DataFrame) -> DataFrame:
        """
        Calculate the 20-period Exponential Moving Average.
        """
        data["EMA20"] = ema(data["Close"], length=20)
        return data

    def _calculate_ema50(self, data: DataFrame) -> DataFrame:
        """
        Calculate the 50-period Exponential Moving Average.
        """
        data["EMA50"] = ema(data["Close"], length=50)
        return data

    def _calculate_ema200(self, data: DataFrame) -> DataFrame:
        """
        Calculate the 200-period Exponential Moving Average.
        """
        data["EMA200"] = ema(data["Close"], length=200)
        return data

    def _calculate_bollinger(self, data: DataFrame) -> DataFrame:
        """
        Calculate Bollinger Bands.

        Returns:
            DataFrame with upper and lower Bollinger Band columns added.
        """
        result = bbands(data["Close"])

        if result is not None:
            data["Bollinger_Upper"] = result.iloc[:, 2]
            data["Bollinger_Lower"] = result.iloc[:, 0]

        return data

    def _calculate_atr(self, data: DataFrame) -> DataFrame:
        """
        Calculate Average True Range (ATR).

        Returns:
            DataFrame with ATR column added.
        """
        data["ATR"] = atr(
            data["High"],
            data["Low"],
            data["Close"],
            length=14,
        )

        return data

    def _calculate_stochastic(self, data: DataFrame) -> DataFrame:
        """
        Calculate the Stochastic Oscillator.

        Returns:
            DataFrame with stochastic %K and %D columns added.
        """
        result = stoch(
            data["High"],
            data["Low"],
            data["Close"],
        )

        if result is not None:
            data["Stoch_K"] = result.iloc[:, 0]
            data["Stoch_D"] = result.iloc[:, 1]

        return data
