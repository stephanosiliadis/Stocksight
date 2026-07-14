# Import local packages.
from src.models.analysis_request import AnalysisRequest
from src.services.analysis_service import AnalysisService


def main():
    request = AnalysisRequest(
        tickers=["AAPL"],
        period="1y",
        indicators=["ema20", "rsi"],
        include_fundamentals=True,
    )
    results = AnalysisService().analyze(request)
    print(results)


if __name__ == "__main__":
    main()
