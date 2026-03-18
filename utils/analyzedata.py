import logging

from pandas import DataFrame
from pandas_ta.overlap.ema import ema
from pandas_ta.momentum.rsi import rsi
from pandas_ta.momentum.macd import macd
from pandas_ta.volatility.bbands import bbands
from pandas_ta.volatility.atr import atr
from pandas_ta.momentum.stoch import stoch

from .cleandata import clean_data

log = logging.getLogger(__name__)

# All supported indicator keys.
ALL_INDICATORS = [
    "bollinger",
    "rsi",
    "macd",
    "ema20",
    "ema50",
    "ema200",
    "volume",
    "atr",
    "stochastic",
    "signals",
    "support_resistance",
]


def analyze_data(stock_data, indicators: list | None = None) -> DataFrame | None:
    """
    Perform technical analysis on the stock data.

    Args:
        stock_data: Raw OHLCV DataFrame from yfinance.
        indicators:  List of indicator keys to compute. Defaults to all.

    Returns:
        DataFrame with new indicator columns appended, or None on failure.
    """
    if indicators is None:
        indicators = ALL_INDICATORS

    if stock_data is None or stock_data.empty:
        log.warning("Stock data is empty or invalid.")
        return None

    stock_data = clean_data(stock_data)

    # ── Bollinger Bands ──────────────────────────────────────────────────────
    if "bollinger" in indicators:
        try:
            bb = bbands(stock_data["Close"])
            if bb is not None:
                stock_data["Bollinger_Upper"] = bb.iloc[:, 2]  # BBU
                stock_data["Bollinger_Lower"] = bb.iloc[:, 0]  # BBL
        except Exception as e:
            log.error(f"Bollinger Bands failed: {e}")

    # ── RSI ──────────────────────────────────────────────────────────────────
    if "rsi" in indicators:
        try:
            stock_data["RSI"] = rsi(stock_data["Close"], length=14)
        except Exception as e:
            log.error(f"RSI failed: {e}")

    # ── MACD ─────────────────────────────────────────────────────────────────
    if "macd" in indicators:
        try:
            m = macd(stock_data["Close"])
            if m is not None:
                stock_data["MACD"] = m.iloc[:, 0]
                stock_data["MACD_Histogram"] = m.iloc[:, 1]
                stock_data["MACD_Signal"] = m.iloc[:, 2]
        except Exception as e:
            log.error(f"MACD failed: {e}")

    # ── EMA 20 ───────────────────────────────────────────────────────────────
    if "ema20" in indicators:
        try:
            stock_data["EMA20"] = ema(stock_data["Close"], length=20)
        except Exception as e:
            log.error(f"EMA20 failed: {e}")

    # ── EMA 50 ───────────────────────────────────────────────────────────────
    if "ema50" in indicators:
        try:
            stock_data["EMA50"] = ema(stock_data["Close"], length=50)
        except Exception as e:
            log.error(f"EMA50 failed: {e}")

    # ── EMA 200 ──────────────────────────────────────────────────────────────
    if "ema200" in indicators:
        try:
            stock_data["EMA200"] = ema(stock_data["Close"], length=200)
        except Exception as e:
            log.error(f"EMA200 failed: {e}")

    # ── ATR ──────────────────────────────────────────────────────────────────
    if "atr" in indicators:
        try:
            stock_data["ATR"] = atr(
                stock_data["High"], stock_data["Low"], stock_data["Close"], length=14
            )
        except Exception as e:
            log.error(f"ATR failed: {e}")

    # ── Stochastic Oscillator ────────────────────────────────────────────────
    if "stochastic" in indicators:
        try:
            st = stoch(stock_data["High"], stock_data["Low"], stock_data["Close"])
            if st is not None:
                stock_data["Stoch_K"] = st.iloc[:, 0]
                stock_data["Stoch_D"] = st.iloc[:, 1]
        except Exception as e:
            log.error(f"Stochastic failed: {e}")

    log.debug(f"Analysis complete. Columns: {list(stock_data.columns)}")
    return stock_data
