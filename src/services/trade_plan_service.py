from __future__ import annotations

import pandas as pd

from src.models.risk_profile import TradePlan, StopLossRecommendation
from src.models.analysis_result import AnalysisResult
from src.services.position_sizing_service import PositionSizingService
from src.services.risk_service import RiskService


class TradePlanService:
    """
    Build a complete trade plan from an AnalysisResult and account parameters.
    """

    def __init__(self, reward_ratio: float = 2.0):
        """
        Args:
            reward_ratio: Risk/reward target ratio (default 2:1 means target is 2x stop distance)
        """
        self.reward_ratio = reward_ratio
        self.position_sizing_service = PositionSizingService()
        self.risk_service = RiskService()

    def build_plan(
        self,
        result: AnalysisResult,
        account_size: float,
        risk_pct: float,
        signal_price: float | None = None,
    ) -> TradePlan | None:
        """
        Build a trade plan from an AnalysisResult.

        Args:
            result: AnalysisResult containing price data, indicators, support/resistance levels
            account_size: Total account size in dollars
            risk_pct: Risk per trade as a fraction (0.01 = 1% risk)
            signal_price: Optional entry price (defaults to last close)

        Returns:
            TradePlan with entry, stop, target, position size, and risk/reward ratio
            Returns None if entry price is invalid
        """
        if result.raw_data is None or result.raw_data.empty:
            return None

        entry_price = signal_price or float(result.raw_data["Close"].iloc[-1])
        if entry_price <= 0:
            return None

        # Determine stop loss
        stop_price, stop_method = self._calculate_stop(result, entry_price)

        # Determine target using reward_ratio or Phase 1 resistance levels
        target_price = self._calculate_target(result, entry_price, stop_price)

        # Calculate position size
        position_size = self.position_sizing_service.serve_position_size(
            account_size, risk_pct, entry_price, stop_price
        )

        # Calculate risk/reward
        risk_reward = self.risk_service.calculate_risk_reward(
            entry_price, stop_price, target_price
        )

        # Create StopLossRecommendation
        stop_rec = StopLossRecommendation(
            stop_price=float(stop_price),
            method=stop_method,
            take_profit_price=float(target_price),
            risk_reward_ratio=float(risk_reward),
        )

        return TradePlan(
            entry_price=float(entry_price),
            stop=stop_rec,
            target=float(target_price),
            position_size=position_size,
            risk_reward=float(risk_reward),
        )

    def _calculate_stop(
        self, result: AnalysisResult, entry_price: float
    ) -> tuple[float, str]:
        """
        Calculate stop loss price with fallback strategy.

        Returns: (stop_price, method_used)
        """
        # Try ATR first
        if "ATR" in result.indicators.columns:
            try:
                atr = float(result.indicators["ATR"].iloc[-1])
                if atr > 0:
                    stop = entry_price - 2 * atr
                    return stop, "atr"
            except Exception:
                pass

        # Fallback: use nearest support level from Phase 1 if available
        if result.support_levels:
            try:
                support = max(
                    [s.price for s in result.support_levels if s.price < entry_price],
                    default=None,
                )
                if support is not None:
                    return float(support), "support_level"
            except Exception:
                pass

        # Final fallback: 5% below entry
        stop = entry_price * 0.95
        return stop, "percent_5"

    def _calculate_target(
        self, result: AnalysisResult, entry_price: float, stop_price: float
    ) -> float:
        """
        Calculate profit target.

        Preference: use nearest resistance level above entry, fall back to reward_ratio.
        """
        # Try Phase 1 resistance levels first
        if result.resistance_levels:
            try:
                targets = [
                    r.price for r in result.resistance_levels if r.price > entry_price
                ]
                if targets:
                    return float(min(targets))
            except Exception:
                pass

        # Fallback: use reward_ratio
        risk_distance = entry_price - stop_price
        target = entry_price + (risk_distance * self.reward_ratio)
        return float(target)
