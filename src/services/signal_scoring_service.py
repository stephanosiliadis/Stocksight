from __future__ import annotations

from typing import List
import pandas as pd

from src.models.scored_signal import ScoredSignal
from src.models.signal import SignalType, Signal
from src.models.analysis_result import AnalysisResult


class SignalScoringService:
    def __init__(self):
        pass

    def score(self, signal: Signal, result: AnalysisResult) -> ScoredSignal:
        score = 0.0
        factors: List[str] = []

        # Trend agreement
        try:
            if result.trend is not None and result.trend.trend is not None:
                if (
                    signal.signal_type == SignalType.BUY
                    and result.trend.trend.name == "BULLISH"
                ):
                    score += 40
                    factors.append("trend_agrees")
                if (
                    signal.signal_type == SignalType.SELL
                    and result.trend.trend.name == "BEARISH"
                ):
                    score += 40
                    factors.append("trend_agrees")
        except Exception:
            pass

        # Regime
        try:
            if result.regime is not None and result.regime.regime.name == "TRENDING":
                score += 30
                factors.append("regime_trending")
        except Exception:
            pass

        # Volume confirmation: compare volume on signal date to trailing 20-day avg
        try:
            date_idx = pd.Timestamp(signal.date)
            data = result.raw_data
            if date_idx in data.index:
                vol_on_date = float(data.loc[date_idx, "Volume"])
                trailing = data.loc[:date_idx].tail(21)["Volume"].iloc[:-1]
                if not trailing.empty and vol_on_date > float(trailing.mean()):
                    score += 30
                    factors.append("volume_confirm")
        except Exception:
            pass

        confidence = max(0.0, min(100.0, score))
        return ScoredSignal(
            signal=signal, confidence=float(confidence), contributing_factors=factors
        )
