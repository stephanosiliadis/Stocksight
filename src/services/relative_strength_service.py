from __future__ import annotations

import pandas as pd

from src.models.relative_strength import RelativeStrength


class RelativeStrengthService:
    def __init__(self, benchmark_ticker: str = "SPY"):
        self.benchmark_ticker = benchmark_ticker

    def serve_relative_strength(
        self, ticker_data: pd.DataFrame, benchmark_data: pd.DataFrame
    ) -> RelativeStrength:
        # Align indices by intersection
        if ticker_data is None or ticker_data.empty:
            return RelativeStrength(
                ticker_return_pct=0.0,
                benchmark_return_pct=0.0,
                relative_pct=0.0,
                outperforming=False,
                benchmark_ticker=self.benchmark_ticker,
            )

        if benchmark_data is None or benchmark_data.empty:
            benchmark_return = 0.0
        else:
            # Use same date range intersection
            start = max(ticker_data.index.min(), benchmark_data.index.min())
            end = min(ticker_data.index.max(), benchmark_data.index.max())
            b = benchmark_data.loc[
                (benchmark_data.index >= start) & (benchmark_data.index <= end)
            ]
            if b.empty:
                benchmark_return = 0.0
            else:
                benchmark_return = (
                    float(b["Close"].iloc[-1] / b["Close"].iloc[0] - 1.0) * 100.0
                )

        t = ticker_data
        t_period = t.loc[t.index >= t.index.min()]
        if t_period.empty:
            ticker_return = 0.0
        else:
            ticker_return = (
                float(t["Close"].iloc[-1] / t["Close"].iloc[0] - 1.0) * 100.0
            )

        relative = ticker_return - benchmark_return
        outperforming = relative > 0

        return RelativeStrength(
            ticker_return_pct=float(ticker_return),
            benchmark_return_pct=float(benchmark_return),
            relative_pct=float(relative),
            outperforming=bool(outperforming),
            benchmark_ticker=self.benchmark_ticker,
        )
