from __future__ import annotations

from pydantic import BaseModel
from typing import List


class VolumeProfile(BaseModel):
    price_bins: List[float]
    volume_at_price: List[float]
    point_of_control: float
    value_area_high: float
    value_area_low: float
