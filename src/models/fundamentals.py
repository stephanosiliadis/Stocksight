# Import third party packages.
from pydantic import BaseModel


class Fundamentals(BaseModel):
    """
    Represents fundamental company information and valuation metrics.

    Attributes:
        pe_ratio: Trailing price-to-earnings ratio.
        market_cap: Total market capitalization of the company.
        w52_high: Highest stock price reached during the last 52 weeks.
        w52_low: Lowest stock price reached during the last 52 weeks.
        dividend_yield: Annual dividend yield expressed as a decimal.
        sector: Economic sector the company belongs to.
        industry: Industry classification of the company.
        beta: Measure of the stock's volatility relative to the market.
        eps: Trailing earnings per share.
        revenue: Total company revenue.
        short_name: Short company name or trading name.
    """

    pe_ratio: float | None
    market_cap: int | None
    w52_high: float | None
    w52_low: float | None
    dividend_yield: float | None
    sector: str | None
    industry: str | None
    beta: float | None
    eps: float | None
    revenue: int | None
    short_name: str | None
