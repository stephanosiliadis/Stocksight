from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, Field


class TrendState(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"


class SupportResistanceLevel(BaseModel):
    price: float
    level_type: str = Field(..., description="'support' or 'resistance'")
    strength: int = Field(1, description="Number of touches or confirmations")
    first_touch: date | None = None
    last_touch: date | None = None


class TrendClassification(BaseModel):
    trend: TrendState
    strength: float = Field(..., ge=0.0, le=100.0, description="0-100 confidence score")
    since: date | None = None


class BreakoutEvent(BaseModel):
    date: datetime
    level: float
    direction: str = Field(..., description="'breakout' or 'breakdown'")
    level_type: str = Field(..., description="'support' or 'resistance'")
