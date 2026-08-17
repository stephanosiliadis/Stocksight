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

    ALL_INDICATORS = [
        "bollinger",
        "rsi",
        "macd",
        "ema20",
        "ema50",
        "ema200",
        "atr",
        "stochastic",
        "volume",
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
            "volume": self._calculate_volume,
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

        data = data.copy()

        if indicators is None:
            indicators = self.ALL_INDICATORS

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
        result = rsi(data["Close"], length=14)

        # pandas_ta returns None (not a NaN-filled Series) when there are
        # fewer rows than `length` -- e.g. a recently-IPO'd ticker with
        # under 14 days of history. Assigning None directly would set the
        # whole column to the scalar None (object dtype), which later
        # breaks any numeric comparison against it with a raw Python
        # TypeError instead of the NaN-safe behavior the rest of this app
        # already relies on. Leaving the column unset is exactly what
        # every downstream consumer already checks for via
        # `"RSI" in data.columns` / `.dropna()`.
        if result is not None:
            data["RSI"] = result

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
        result = ema(data["Close"], length=20)
        # See _calculate_rsi's comment: pandas_ta returns None rather
        # than an all-NaN Series when there isn't enough history.
        if result is not None:
            data["EMA20"] = result
        return data

    def _calculate_ema50(self, data: DataFrame) -> DataFrame:
        """
        Calculate the 50-period Exponential Moving Average.
        """
        result = ema(data["Close"], length=50)
        if result is not None:
            data["EMA50"] = result
        return data

    def _calculate_ema200(self, data: DataFrame) -> DataFrame:
        """
        Calculate the 200-period Exponential Moving Average.

        Needs 200 rows of history to produce anything -- a ticker with
        less (e.g. recently IPO'd) simply won't get an EMA200 column at
        all, which TrendService and the technical chart already treat as
        "not available" rather than crashing on.
        """
        result = ema(data["Close"], length=200)
        if result is not None:
            data["EMA200"] = result
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
        result = atr(
            data["High"],
            data["Low"],
            data["Close"],
            length=14,
        )

        if result is not None:
            data["ATR"] = result

        return data

    def _calculate_volume(self, data: DataFrame) -> DataFrame:
        """
        No-op indicator for Volume.

        Volume is already present in the raw OHLCV data, so no extra
        calculation is required. This method exists to keep Volume in the
        indicator pipeline and allow the UI selection to be validated.
        """
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
