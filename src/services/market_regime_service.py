from __future__ import annotations

from typing import Optional
import numpy as np
import pandas as pd

from src.models.market_regime import MarketRegime, RegimeClassification


class MarketRegimeService:
    def __init__(self, atr_window: int = 14, trend_lookback: int = 20):
        self.atr_window = atr_window
        self.trend_lookback = trend_lookback

    def classify(self, data: pd.DataFrame) -> RegimeClassification:
        if data is None or data.empty:
            return RegimeClassification(regime=MarketRegime.RANGING, confidence=0.0)

        # Compute ATR
        high = data["High"]
        low = data["Low"]
        close = data["Close"]
        prev_close = close.shift(1)
        tr = pd.concat(
            [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
            axis=1,
        ).max(axis=1)
        atr = tr.rolling(window=self.atr_window).mean().iloc[-1]
        close_now = close.iloc[-1]
        atr_pct = float(atr / close_now) if close_now != 0 else 0.0

        # Linear fit to closes for slope and R^2
        closes = close.dropna()
        if len(closes) < self.trend_lookback:
            slope = 0.0
            r2 = 0.0
        else:
            y = closes.values[-self.trend_lookback :]
            x = np.arange(len(y))
            coeffs = np.polyfit(x, y, 1)
            slope = coeffs[0]
            y_hat = np.polyval(coeffs, x)
            ss_res = np.sum((y - y_hat) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r2 = float(1 - ss_res / ss_tot) if ss_tot != 0 else 0.0

        # Heuristics
        # Volatile if ATR% > 0.02 (2%)
        if atr_pct >= 0.02:
            regime = MarketRegime.VOLATILE
            confidence = min(100.0, atr_pct * 5000)
            return RegimeClassification(regime=regime, confidence=confidence)

        # Trending if R^2 is high and slope magnitude relative to price > small threshold
        slope_pct = abs(slope / close_now) if close_now != 0 else 0.0
        if r2 >= 0.6 and slope_pct >= 0.002:
            regime = MarketRegime.TRENDING
            confidence = min(100.0, 50.0 + r2 * 50.0)
            return RegimeClassification(regime=regime, confidence=confidence)

        # Otherwise ranging/choppy
        regime = MarketRegime.RANGING
        confidence = max(0.0, min(100.0, (1 - r2) * 50.0))
        return RegimeClassification(regime=regime, confidence=float(confidence))
