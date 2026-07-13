# Import standard library packages.
from datetime import date

# Import third party packages.
from pydantic import BaseModel


class Statistics(BaseModel):
    """
    Represents summary price statistics for the analyzed period.

    Attributes:
        period_high: Highest closing price observed during the analysis period.
        period_high_date: Date on which the period high occurred.
        period_low: Lowest closing price observed during the analysis period.
        period_low_date: Date on which the period low occurred.
        current_close: Most recent closing price available in the dataset.
        pct_from_high: Percentage difference between the current close and the period high.
        pct_from_low: Percentage difference between the current close and the period low.
    """

    period_high: float
    period_high_date: date
    period_low: float
    period_low_date: date
    current_close: float
    pct_from_high: float
    pct_from_low: float
