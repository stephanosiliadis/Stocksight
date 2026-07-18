from __future__ import annotations

from pydantic import BaseModel, Field
from src.models.signal import Signal
from typing import List


class ScoredSignal(BaseModel):
    signal: Signal
    confidence: float = Field(..., ge=0.0, le=100.0)
    contributing_factors: List[str] = Field(default_factory=list)
