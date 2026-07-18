from __future__ import annotations

from datetime import datetime
from typing import List, Tuple

import pandas as pd

from src.models.market_structure import (
    SupportResistanceLevel,
    BreakoutEvent,
)


class SupportResistanceService:
    def __init__(self, cluster_tol: float = 0.015):
        # cluster_tol: fraction (e.g., 0.015 == 1.5%)
        self.cluster_tol = cluster_tol

    def serve_levels(
        self, data: pd.DataFrame, window: int = 20, num_levels: int = 3
    ) -> Tuple[List[SupportResistanceLevel], List[SupportResistanceLevel]]:
        if data is None or data.empty:
            return [], []

        rolling_high = data["High"].rolling(window=window, center=True).max()
        rolling_low = data["Low"].rolling(window=window, center=True).min()
        resistance_mask = data["High"] == rolling_high
        support_mask = data["Low"] == rolling_low

        resistance_candidates = [
            (float(price), pd.Timestamp(idx).to_pydatetime())
            for idx, price in data.loc[resistance_mask, "High"].items()
        ]
        support_candidates = [
            (float(price), pd.Timestamp(idx).to_pydatetime())
            for idx, price in data.loc[support_mask, "Low"].items()
        ]

        resistances = self._cluster_candidates(resistance_candidates, "resistance")
        supports = self._cluster_candidates(support_candidates, "support")

        # Keep top N by strength
        resistances = sorted(resistances, key=lambda s: s.strength, reverse=True)[
            :num_levels
        ]
        supports = sorted(supports, key=lambda s: s.strength, reverse=True)[:num_levels]

        return supports, resistances

    def _cluster_candidates(self, candidates, level_type: str):
        # candidates: list of (price, datetime)
        if not candidates:
            return []

        # Sort by price
        candidates = sorted(candidates, key=lambda x: x[0])
        clusters: list[list[tuple[float, datetime]]] = []

        for price, dt in candidates:
            placed = False
            for cluster in clusters:
                center = sum(p for p, _ in cluster) / len(cluster)
                if abs(price - center) / center <= self.cluster_tol:
                    cluster.append((price, dt))
                    placed = True
                    break
            if not placed:
                clusters.append([(price, dt)])

        levels = []
        for cluster in clusters:
            prices = [p for p, _ in cluster]
            dates = [d for _, d in cluster]
            level_price = float(sum(prices) / len(prices))
            strength = len(cluster)
            first_touch = min(dates).date()
            last_touch = max(dates).date()
            levels.append(
                SupportResistanceLevel(
                    price=level_price,
                    level_type=level_type,
                    strength=strength,
                    first_touch=first_touch,
                    last_touch=last_touch,
                )
            )

        return levels

    def detect_breakouts(
        self,
        data: pd.DataFrame,
        levels: list[SupportResistanceLevel],
        pct_threshold: float = 0.01,
        lookback: int = 3,
    ) -> list[BreakoutEvent]:
        events: list[BreakoutEvent] = []
        if data is None or data.empty or not levels:
            return events

        closes = data["Close"]
        for level in levels:
            price = level.price
            # Check last `lookback` closes were within band
            if len(closes) < lookback + 1:
                continue
            recent = closes.iloc[-(lookback + 1) :]
            before = recent.iloc[:-1]
            last = recent.iloc[-1]
            band_low = price * (1 - pct_threshold)
            band_high = price * (1 + pct_threshold)
            if all(band_low <= v <= band_high for v in before):
                if last > band_high:
                    events.append(
                        BreakoutEvent(
                            date=pd.Timestamp(recent.index[-1]).to_pydatetime(),
                            level=price,
                            direction="breakout",
                            level_type=level.level_type,
                        )
                    )
                elif last < band_low:
                    events.append(
                        BreakoutEvent(
                            date=pd.Timestamp(recent.index[-1]).to_pydatetime(),
                            level=price,
                            direction="breakdown",
                            level_type=level.level_type,
                        )
                    )

        return events
