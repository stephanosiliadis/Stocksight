from __future__ import annotations

from pydantic import BaseModel, Field

# Mirrors analysis_service.py's own DEFAULT_INDICATORS, so a user who has
# never visited Settings sees identical behavior to before Settings
# existed.
_FALLBACK_INDICATORS = ["ema20", "ema50", "rsi", "macd"]


class AppSettings(BaseModel):
    """
    User-configurable preferences, persisted across sessions.

    Attributes:
        default_indicators: Indicators pre-checked on the Stock Analysis
            page's indicator selector.
        default_account_size: Default account size ($) pre-filled in the
            Trade Plan risk inputs (Phase 3's PositionSizingService).
        default_risk_pct: Default risk per trade, as a FRACTION (0.01 ==
            1%), matching the convention used throughout risk_profile.py,
            PositionSizingService, and TradePlanService.
    """

    default_indicators: list[str] = Field(
        default_factory=lambda: list(_FALLBACK_INDICATORS)
    )
    default_account_size: float = 10_000.0
    default_risk_pct: float = Field(default=0.01, ge=0.0, le=1.0)
