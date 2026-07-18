from datetime import date, datetime

from src.models.market_structure import (
    SupportResistanceLevel,
    TrendClassification,
    TrendState,
    BreakoutEvent,
)


def main() -> None:
    s = SupportResistanceLevel(
        price=150.0,
        level_type="support",
        strength=3,
        first_touch=date(2025, 1, 10),
        last_touch=date(2025, 6, 1),
    )
    r = SupportResistanceLevel(
        price=180.0,
        level_type="resistance",
        strength=2,
        first_touch=date(2024, 12, 1),
        last_touch=date(2025, 5, 20),
    )
    t = TrendClassification(
        trend=TrendState.BULLISH, strength=78.5, since=date(2025, 4, 1)
    )
    b = BreakoutEvent(
        date=datetime(2025, 6, 15, 14, 30),
        level=180.0,
        direction="breakout",
        level_type="resistance",
    )

    print("Support:", s)
    print("Resistance:", r)
    print("Trend:", t)
    print("Breakout:", b)


if __name__ == "__main__":
    main()
