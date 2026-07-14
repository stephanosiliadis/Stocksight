# Import local packages.
from src.models.analysis_request import AnalysisRequest
from src.services.analysis_service import AnalysisService
from src.visualization.comparison_chart import ComparisonChart
from src.visualization.technical_chart import TechnicalChart


def main():
    request = AnalysisRequest(
        tickers=["AAPL", "MSFT"],
        period="1y",
        indicators=[
            "ema20",
            "ema50",
            "rsi",
            "macd",
            "atr",
        ],
        include_fundamentals=True,
    )

    results = AnalysisService().analyze(request)

    for result in results:
        chart = TechnicalChart(
            data=result.indicators,
            ticker=result.ticker,
            indicators=request.indicators or [],
            signals=result.signals,
        )

        figure = chart.build()

        print(f"{result.ticker}: " f"{type(figure).__name__}")

    comparison_data = {}

    for result in results:
        normalized = result.raw_data["Close"] / result.raw_data["Close"].iloc[0] * 100

        comparison_data[result.ticker] = normalized

    comparison_chart = ComparisonChart(
        normalized_data=comparison_data,
    )

    comparison_figure = comparison_chart.build()

    print(f"Comparison chart: " f"{type(comparison_figure).__name__}")


if __name__ == "__main__":
    main()
