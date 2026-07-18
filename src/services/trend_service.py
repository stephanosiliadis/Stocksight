from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.models.market_structure import TrendClassification, TrendState


class TrendService:
    def __init__(self, lookback: int = 10):
        self.lookback = lookback

    def classify(self, data: pd.DataFrame) -> TrendClassification:
        """
        Classify trend using EMA50 vs EMA200 relationship and recent slopes.

        Returns SIDEWAYS with strength 0 if EMA columns are missing.
        Strength is a heuristic combining the percent gap between EMAs
        and their recent average slope, mapped to 0-100.
        """
        if data is None or data.empty:
            return TrendClassification(
                trend=TrendState.SIDEWAYS, strength=0.0, since=None
            )

        if not all(col in data.columns for col in ("EMA50", "EMA200")):
            return TrendClassification(
                trend=TrendState.SIDEWAYS, strength=0.0, since=None
            )

        ema50 = data["EMA50"].dropna()
        ema200 = data["EMA200"].dropna()
        if len(ema50) < self.lookback or len(ema200) < self.lookback:
            return TrendClassification(
                trend=TrendState.SIDEWAYS, strength=0.0, since=None
            )

        try:
            last50 = float(ema50.iloc[-1])
            last200 = float(ema200.iloc[-1])
            prev50 = float(ema50.iloc[-self.lookback])
            prev200 = float(ema200.iloc[-self.lookback])
        except Exception:
            return TrendClassification(
                trend=TrendState.SIDEWAYS, strength=0.0, since=None
            )

        slope50 = (last50 / prev50 - 1.0) if prev50 != 0 else 0.0
        slope200 = (last200 / prev200 - 1.0) if prev200 != 0 else 0.0

        gap_pct = abs(last50 - last200) / last200 if last200 != 0 else 0.0

        # Heuristic strength: weight gap and slope (scale to 0-100)
        strength_raw = gap_pct * 200.0 + (abs(slope50) + abs(slope200)) * 100.0
        strength = max(0.0, min(100.0, strength_raw))

        if last50 > last200 and slope50 > 0 and slope200 > 0:
            trend = TrendState.BULLISH
        elif last50 < last200 and slope50 < 0 and slope200 < 0:
            trend = TrendState.BEARISH
        else:
            trend = TrendState.SIDEWAYS

        # `since` is approximated as when the EMA relationship last flipped
        since = None
        try:
            # find most recent index where sign(last50-last200) changed
            diff = (ema50 - ema200).dropna()
            if not diff.empty:
                sign = diff.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
                changes = sign[sign != sign.shift(1)].dropna()
                if not changes.empty:
                    since = pd.Timestamp(changes.index[-1]).date()
        except Exception:
            since = None

        return TrendClassification(trend=trend, strength=float(strength), since=since)
