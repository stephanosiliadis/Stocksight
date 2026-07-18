from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class MarketRegime(str, Enum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"


class RegimeClassification(BaseModel):
    regime: MarketRegime
    confidence: float = Field(..., ge=0.0, le=100.0)
