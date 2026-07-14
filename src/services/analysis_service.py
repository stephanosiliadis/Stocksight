# Import standard library packages.
from datetime import date

# Import third party packages.
import pandas as pd
from dateutil.relativedelta import relativedelta

# Import local packages.
from src.models.analysis_request import AnalysisRequest
from src.models.analysis_result import AnalysisResult
from src.services.backtest_service import BacktestService
from src.services.data_service import DataService
from src.services.financials_service import FinancialsService
from src.services.fundamentals_service import FundamentalsService
from src.services.indicator_service import IndicatorService
from src.services.signal_service import SignalService
from src.services.statistics_service import StatisticsService
from src.utils.validators import (
    ValidationError,
    validate_backtest_capital,
    validate_date_range,
    validate_indicators,
    validate_period,
    validate_tickers,
)

DEFAULT_INDICATORS = [
    "ema20",
    "ema50",
    "rsi",
    "macd",
]

# Single source of truth for supported periods, in the "1m" style used
# throughout validators.py (not "1mo").
PERIOD_MAPPING = {
    "1m": relativedelta(months=1),
    "3m": relativedelta(months=3),
    "6m": relativedelta(months=6),
    "1y": relativedelta(years=1),
    "2y": relativedelta(years=2),
    "5y": relativedelta(years=5),
    "10y": relativedelta(years=10),
}


class AnalysisService:
    def __init__(self):
        self.data_service = DataService()
        self.indicator_service = IndicatorService()
        self.signal_service = SignalService()
        self.statistics_service = StatisticsService()
        self.fundamentals_service = FundamentalsService()
        self.financials_service = FinancialsService()
        self.backtest_service = BacktestService()
        # Populated by analyze() with {ticker: error_message} for any ticker
        # that failed in isolation without aborting the rest of the batch.
        self.failures: dict[str, str] = {}

    def analyze(
        self,
        request: AnalysisRequest,
    ) -> list[AnalysisResult]:
        self.failures = {}

        tickers = validate_tickers(request.tickers)

        if request.backtest:
            validate_backtest_capital(request.initial_capital)

        start_date, end_date = self._resolve_dates(
            request.start_date,
            request.end_date,
            request.period,
        )
        indicators = self._prepare_indicators(request.indicators)
        warmup_start = self._calculate_warmup_start(
            start_date,
            indicators,
        )

        responses: list[AnalysisResult] = []
        for ticker in tickers:
            try:
                result = self._analyze_ticker(
                    ticker=ticker,
                    request=request,
                    indicators=indicators,
                    start_date=start_date,
                    end_date=end_date,
                    warmup_start=warmup_start,
                )
            except Exception as exc:
                # Per-ticker isolation: one bad ticker (bad data, network
                # error, unexpected computation failure) must not abort the
                # rest of the batch.
                self.failures[ticker] = str(exc)
                continue

            if result is not None:
                responses.append(result)

        return responses

    def _analyze_ticker(
        self,
        ticker: str,
        request: AnalysisRequest,
        indicators: list[str],
        start_date: date,
        end_date: date,
        warmup_start: date,
    ) -> AnalysisResult | None:
        raw_data = self.data_service.serve_stock_data(
            ticker=ticker,
            start_date=warmup_start.isoformat(),
            end_date=end_date.isoformat(),
        )

        if raw_data is None or raw_data.empty:
            return None

        indicator_data = self.indicator_service.serve_indicators(
            raw_data,
            indicators,
        )

        if indicator_data is None or indicator_data.empty:
            return None

        signals = self.signal_service.serve_signals(
            indicator_data,
            indicators,
            ticker,
        )
        visible_data = raw_data.loc[raw_data.index >= pd.Timestamp(start_date)]
        visible_indicators = indicator_data.loc[
            indicator_data.index >= pd.Timestamp(start_date)
        ]
        statistics = self.statistics_service.serve_statistics(visible_data)

        if statistics is None:
            return None

        fundamentals = None
        if request.include_fundamentals:
            fundamentals = self.fundamentals_service.serve_fundamentals(ticker)

        financial_statements = None
        if request.include_statements:
            financial_statements = self.financials_service.serve_financial_statements(
                ticker
            )

        backtest_result = None
        if request.backtest:
            backtest_result = self.backtest_service.serve_backtest(
                ticker=ticker,
                data=visible_data,
                signals=signals,
                initial_capital=request.initial_capital,
            )

        return AnalysisResult(
            ticker=ticker,
            raw_data=visible_data,
            active_indicators=request.indicators,
            indicators=visible_indicators,
            signals=signals,
            statistics=statistics,
            fundamentals=fundamentals,
            financial_statements=financial_statements,
            backtest_result=backtest_result,
        )

    def _resolve_dates(
        self,
        start_date: date | None,
        end_date: date | None,
        period: str | None,
    ) -> tuple[date, date]:

        if start_date and end_date:
            validate_date_range(start_date.isoformat(), end_date.isoformat())
            return start_date, end_date

        today = date.today()
        validated_period = validate_period(
            period or "1y",
            period_map=PERIOD_MAPPING,
        )

        if validated_period is None:
            # validate_period only returns None when passed None, which
            # can't happen here since we always supply a default above.
            raise ValidationError(f"Unsupported period '{period}'")

        return (
            today - PERIOD_MAPPING[validated_period],
            today,
        )

    def _prepare_indicators(
        self,
        indicators: list[str] | None,
    ) -> list[str]:

        if not indicators:
            indicators = DEFAULT_INDICATORS.copy()

        validated = validate_indicators(
            indicators,
            allowed=IndicatorService.ALL_INDICATORS,
        )

        if validated is None:
            raise ValidationError("No valid indicators were selected.")

        return validated

    def _calculate_warmup_start(
        self,
        start_date: date,
        indicators: list[str],
    ) -> date:
        max_warmup_days = 0
        warmup_requirements = {
            "ema20": 20,
            "ema50": 50,
            "ema200": 200,
            "rsi": 30,
            "macd": 60,
            "atr": 30,
            "stochastic": 30,
            "bollinger": 30,
        }
        for indicator in indicators:
            if indicator in warmup_requirements:
                max_warmup_days = max(
                    max_warmup_days,
                    warmup_requirements[indicator],
                )

        # Rough conversion from trading days to calendar days.
        calendar_days = int(max_warmup_days * 1.5)
        return start_date - relativedelta(days=calendar_days)
