import numpy as np
import pandas as pd
import logging

log = logging.getLogger(__name__)


def detect_signals(data: pd.DataFrame, indicators: list) -> pd.DataFrame:
    """
    Detect buy/sell signals based on active indicators.

    Sources:
        - RSI: crossing back above 30 (buy) or below 70 (sell)
        - MACD: MACD line crossing above/below signal line
        - EMA: Golden cross (EMA50 > EMA200) / Death cross (EMA50 < EMA200)

    Signals are plotted just outside the candle so markers don't overlap price.
    NaN values in any indicator series are treated as False so comparisons never
    receive None operands (which raises TypeError in pandas/numexpr).
    """
    signals = pd.DataFrame(index=data.index)
    signals["Buy"] = np.nan
    signals["Sell"] = np.nan

    def _safe(series: pd.Series) -> pd.Series:
        """Return a boolean series with NaN rows set to False."""
        return series.fillna(False)

    # RSI signals: price crossing back into normal range from extreme
    if "rsi" in indicators and "RSI" in data.columns:
        rsi = data["RSI"]
        rsi_buy = _safe((rsi.shift(1) < 30) & (rsi >= 30))
        rsi_sell = _safe((rsi.shift(1) > 70) & (rsi <= 70))
        signals.loc[rsi_buy, "Buy"] = data.loc[rsi_buy, "Low"] * 0.985
        signals.loc[rsi_sell, "Sell"] = data.loc[rsi_sell, "High"] * 1.015

    # MACD crossovers
    if (
        "macd" in indicators
        and "MACD" in data.columns
        and "MACD_Signal" in data.columns
    ):
        macd = data["MACD"]
        macd_sig = data["MACD_Signal"]
        macd_buy = _safe((macd.shift(1) < macd_sig.shift(1)) & (macd >= macd_sig))
        macd_sell = _safe((macd.shift(1) > macd_sig.shift(1)) & (macd <= macd_sig))
        signals.loc[macd_buy & signals["Buy"].isna(), "Buy"] = (
            data.loc[macd_buy & signals["Buy"].isna(), "Low"] * 0.985
        )
        signals.loc[macd_sell & signals["Sell"].isna(), "Sell"] = (
            data.loc[macd_sell & signals["Sell"].isna(), "High"] * 1.015
        )

    # EMA Golden / Death cross
    if all(k in indicators for k in ("ema50", "ema200")) and all(
        c in data.columns for c in ("EMA50", "EMA200")
    ):
        ema50 = data["EMA50"]
        ema200 = data["EMA200"]
        # Only compute cross on rows where both EMAs have a valid value
        both_valid = ema50.notna() & ema200.notna()
        golden = _safe(
            both_valid & (ema50.shift(1) < ema200.shift(1)) & (ema50 >= ema200)
        )
        death = _safe(
            both_valid & (ema50.shift(1) > ema200.shift(1)) & (ema50 <= ema200)
        )
        signals.loc[golden & signals["Buy"].isna(), "Buy"] = (
            data.loc[golden & signals["Buy"].isna(), "Low"] * 0.985
        )
        signals.loc[death & signals["Sell"].isna(), "Sell"] = (
            data.loc[death & signals["Sell"].isna(), "High"] * 1.015
        )

    buy_count = signals["Buy"].notna().sum()
    sell_count = signals["Sell"].notna().sum()
    log.debug(f"Signals detected — Buy: {buy_count}, Sell: {sell_count}")

    return signals


def detect_support_resistance(
    data: pd.DataFrame,
    window: int = 20,
    num_levels: int = 3,
) -> tuple[list, list]:
    """
    Detect key support and resistance levels via rolling window extrema.

    Returns:
        (support_levels, resistance_levels) — sorted lists of price levels.
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

    log.debug(f"Support levels: {support_levels}")
    log.debug(f"Resistance levels: {resistance_levels}")

    return support_levels, resistance_levels
