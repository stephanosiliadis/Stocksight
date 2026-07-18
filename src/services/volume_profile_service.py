from __future__ import annotations

from typing import List
import numpy as np
import pandas as pd

from src.models.volume_profile import VolumeProfile


class VolumeProfileService:
    def serve_profile(self, data: pd.DataFrame, num_bins: int = 20) -> VolumeProfile:
        if data is None or data.empty:
            return VolumeProfile(
                price_bins=[],
                volume_at_price=[],
                point_of_control=0.0,
                value_area_high=0.0,
                value_area_low=0.0,
            )

        closes = data["Close"].values
        volumes = data["Volume"].values
        min_price = float(np.min(closes))
        max_price = float(np.max(closes))
        if min_price == max_price:
            bins = np.array([min_price, max_price])
        else:
            bins = np.linspace(min_price, max_price, num_bins + 1)

        vol_per_bin = np.zeros(len(bins) - 1)
        for i in range(len(bins) - 1):
            mask = (closes >= bins[i]) & (closes < bins[i + 1])
            vol_per_bin[i] = float(np.sum(volumes[mask]))

        # include rightmost edge
        mask = closes == max_price
        if mask.any():
            vol_per_bin[-1] += float(np.sum(volumes[mask]))

        bin_centers = ((bins[:-1] + bins[1:]) / 2.0).tolist()
        vol_list = vol_per_bin.tolist()

        # point of control
        poc_idx = int(np.argmax(vol_per_bin))
        point_of_control = float(bin_centers[poc_idx]) if bin_centers else 0.0

        # value area ~70% of total volume
        total_vol = float(np.sum(vol_per_bin))
        if total_vol == 0:
            return VolumeProfile(
                price_bins=bin_centers,
                volume_at_price=vol_list,
                point_of_control=point_of_control,
                value_area_high=point_of_control,
                value_area_low=point_of_control,
            )

        sorted_idx = np.argsort(-vol_per_bin)
        cum = 0.0
        selected = set()
        for idx in sorted_idx:
            cum += vol_per_bin[idx]
            selected.add(idx)
            if cum / total_vol >= 0.7:
                break

        selected_bins = [bins[i] for i in selected] + [bins[max(selected) + 1]]
        value_area_low = float(min(selected_bins))
        value_area_high = float(max(selected_bins))

        return VolumeProfile(
            price_bins=bin_centers,
            volume_at_price=vol_list,
            point_of_control=point_of_control,
            value_area_high=value_area_high,
            value_area_low=value_area_low,
        )
