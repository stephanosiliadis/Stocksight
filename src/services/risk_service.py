from __future__ import annotations


class RiskService:
    """Pure calculation service for risk/reward metrics."""

    @staticmethod
    def calculate_risk_reward(
        entry_price: float, stop_price: float, target_price: float
    ) -> float:
        """
        Calculate risk/reward ratio for a long position.

        Args:
            entry_price: Entry price
            stop_price: Stop loss price
            target_price: Take profit / target price

        Returns:
            Risk/reward ratio: (target - entry) / (entry - stop)
            Returns 0.0 if stop >= entry (invalid trade setup)
        """
        risk = entry_price - stop_price
        if risk <= 0:
            return 0.0

        reward = target_price - entry_price
        if reward <= 0:
            return 0.0

        return float(reward / risk)
