from __future__ import annotations

from pydantic import BaseModel, Field

# Convention (Phase 3, Day 1): ``risk_pct`` is a FRACTION (0.01 == 1%),
# NOT a whole percent (1.0). The same fraction is used end to end by
# PositionSizingService, TradePlanService, and the risk panel so the
# user-supplied "1%" never silently becomes "100%".
VALID_RISK_PCT_RANGE = (0.0, 1.0)


class PositionSizeRecommendation(BaseModel):
    """Position size recommendation in shares, dollars, and at-risk amount.

    Attributes:
        shares: Whole-share count produced by ``floor(risk_amount / stop_distance)``.
        dollar_amount: Notional cost of the position at entry (``shares * entry``).
        risk_amount: Dollar amount the trade puts at risk
            (``account_size * risk_pct``), not the actual realized P&L.
        risk_pct: Risk tolerance as a FRACTION (0.01 == 1%).
    """

    shares: int
    dollar_amount: float
    risk_amount: float
    risk_pct: float = Field(..., ge=VALID_RISK_PCT_RANGE[0], le=VALID_RISK_PCT_RANGE[1])


class StopLossRecommendation(BaseModel):
    """Stop loss and take profit pair with the method used to derive them.

    Attributes:
        stop_price: Stop loss price per share.
        method: Identifier of the method that produced the stop. One of
            ``"atr"``, ``"support_level"``, or ``"percent_5"`` so a UI
            can show *why* the stop sits where it does.
        take_profit_price: Profit target per share.
        risk_reward_ratio: ``(target - entry) / (entry - stop)`` for longs.
    """

    stop_price: float
    method: str = Field(..., description="e.g. 'atr', 'support_level', 'percent_5'")
    take_profit_price: float
    risk_reward_ratio: float


class TradePlan(BaseModel):
    """End-to-end trade plan: where to enter, where to stop, what to target.

    Attributes:
        entry_price: Entry price per share (default: last close).
        stop: Stop loss recommendation, including the method used.
        target: Take profit price per share.
        position_size: Position sizing recommendation.
        risk_reward: Risk/reward ratio, copied from ``stop.risk_reward_ratio``
            so callers don't have to dig into the nested stop object.
    """

    entry_price: float
    stop: StopLossRecommendation
    target: float
    position_size: PositionSizeRecommendation
    risk_reward: float
