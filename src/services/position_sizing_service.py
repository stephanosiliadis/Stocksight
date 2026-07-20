from __future__ import annotations

import math

from src.models.risk_profile import PositionSizeRecommendation


class PositionSizingService:
    """
    Calculate position size based on account risk tolerance.

    Convention: risk_pct is a FRACTION (0.01 == 1% risk), not a percent
    (1.0). The same convention is enforced by ``risk_profile.PositionSizeRecommendation``
    and used by ``TradePlanService`` so the user-supplied 1% is never
    silently treated as 100%.
    """

    @staticmethod
    def serve_position_size(
        account_size: float,
        risk_pct: float,
        entry_price: float,
        stop_price: float,
    ) -> PositionSizeRecommendation:
        """
        Calculate position size recommendation.

        Args:
            account_size: Total account size in dollars.
            risk_pct: Risk as a fraction (0.01 == 1% risk, not 1.0).
            entry_price: Entry price per share.
            stop_price: Stop loss price per share.

        Returns:
            ``PositionSizeRecommendation`` with shares and dollar amounts.
            When ``stop_price`` is invalid (>= entry, or entry is non-positive)
            the result is a zero-share plan -- callers should treat that as
            "do not take this trade", not as a crash.
        """
        # Guard against nonsense inputs: keep returning a typed model so
        # callers can render an empty plan instead of guarding every site.
        if account_size <= 0 or entry_price <= 0:
            return PositionSizeRecommendation(
                shares=0,
                dollar_amount=0.0,
                risk_amount=0.0,
                risk_pct=float(risk_pct),
            )

        risk_amount = account_size * risk_pct
        risk_distance = abs(entry_price - stop_price)

        if risk_distance <= 0:
            return PositionSizeRecommendation(
                shares=0,
                dollar_amount=0.0,
                risk_amount=float(risk_amount),
                risk_pct=float(risk_pct),
            )

        # ``math.floor`` matches the spec: shares is rounded down to the
        # nearest whole share, never up. Using int(...) would round
        # toward zero and could oversize a position on tiny stop distances.
        shares = math.floor(risk_amount / risk_distance)
        if shares < 0:
            shares = 0

        dollar_amount = float(shares) * float(entry_price)

        return PositionSizeRecommendation(
            shares=int(shares),
            dollar_amount=float(dollar_amount),
            risk_amount=float(risk_amount),
            risk_pct=float(risk_pct),
        )
