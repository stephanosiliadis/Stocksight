# Import standard library packages.
from datetime import datetime
from enum import Enum

# Import third party packages.
from pydantic import BaseModel


class SignalType(Enum):
    """
    Enumeration representing the possible trading signals.

    Attributes:
        BUY: Indicates a buy signal.
        SELL: Indicates a sell signal.
    """

    BUY = "BUY"
    SELL = "SELL"


class Signal(BaseModel):
    """
    Represents a generated trading signal for a stock.

    Attributes:
        ticker: Stock ticker symbol associated with the signal.
        date: Timestamp when the signal was generated.
        signal_type: Type of trading signal (buy or sell).
        price: Asset price at the time the signal was generated.
        reason: Explanation describing why the signal was generated.
    """

    ticker: str
    date: datetime
    signal_type: SignalType
    price: float
    reason: str
