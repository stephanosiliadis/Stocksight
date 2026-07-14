# Import standard library packages.
from dataclasses import dataclass


@dataclass(frozen=True)
class ChartTheme:
    """
    Visual styling constants shared across all technical analysis charts.

    Centralizing these here means TechnicalChart and IndicatorPlots always
    render indicators with the same colors, instead of each file keeping
    its own copy of the palette.

    Attributes:
        bullish: Color for bullish candles, buy signals, and rising bars.
        bearish: Color for bearish candles, sell signals, and falling bars.
        blue: Primary oscillator line color (RSI, MACD line).
        orange: Secondary oscillator line color (Stochastic %K, MACD signal).
        purple: Bollinger Band line color.
        cyan: EMA 20 line color.
        lime: EMA 50 line color / oversold threshold color.
        tomato: EMA 200 line color / overbought threshold / Stochastic %D color.
        gold: ATR line color.
        oscillator_ratio: Relative panel height for the RSI/Stochastic row.
        candle_ratio: Relative panel height for the main candlestick panel.
        secondary_ratio: Relative panel height for Volume/MACD/ATR rows.
    """

    bullish: str = "#26a69a"
    bearish: str = "#ef5350"
    blue: str = "royalblue"
    orange: str = "darkorange"
    purple: str = "mediumpurple"
    cyan: str = "deepskyblue"
    lime: str = "limegreen"
    tomato: str = "tomato"
    gold: str = "goldenrod"

    oscillator_ratio: float = 1.0
    candle_ratio: float = 4.0
    secondary_ratio: float = 1.0

    palette: tuple[str, ...] = (
        "#2196F3",
        "#FF5722",
        "#4CAF50",
        "#9C27B0",
        "#FF9800",
        "#00BCD4",
        "#F44336",
        "#8BC34A",
    )
