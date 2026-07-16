# Import standard library packages.
from __future__ import annotations

import tempfile
from datetime import datetime

# Import third party packages.
import pandas as pd
import plotly.graph_objects as go
from fpdf import FPDF

# Import local packages.
from src.models.analysis_result import AnalysisResult
from src.models.backtest_result import BacktestResult
from src.models.financial_statements import FinancialStatement
from src.models.fundamentals import Fundamentals
from src.models.statistics import Statistics
from src.reporting.pdf_components import (
    draw_backtest_kpis,
    draw_badges,
    draw_banner,
    draw_financial_table,
    draw_image,
    draw_key_value_table,
    draw_paragraph,
    draw_section_header,
    draw_title,
    draw_trade_log,
)
from src.reporting.trend_commentator import TrendCommentator
from src.visualization.technical_chart import TechnicalChart

# Human-readable labels for the "Indicators: ..." badge line on the cover.
_INDICATOR_LABELS = {
    "bollinger": "Bollinger Bands",
    "rsi": "RSI (14)",
    "macd": "MACD",
    "ema20": "EMA 20",
    "ema50": "EMA 50",
    "ema200": "EMA 200",
    "atr": "ATR (14)",
    "stochastic": "Stochastic Oscillator",
}


class PDFExporter:
    """
    Generates a full multi-section PDF report from a list of AnalysisResult.

    For each ticker: a banner, key statistics, historical range, company
    fundamentals, financial statements (income/balance/cash flow), plain-
    English technical commentary, backtest results (if run), and the
    technical chart. An optional multi-ticker comparison chart can be
    included on the cover page.

    Returns bytes so callers can save the file, stream it through
    Streamlit, or attach it elsewhere. The only filesystem use is the temp
    PNG files FPDF itself requires for embedding chart images.
    """

    def __init__(
        self,
        results: list[AnalysisResult],
        comparison_figure: go.Figure | None = None,
    ) -> None:
        """
        Args:
            results: Analysis results to report on, one page per ticker.
            comparison_figure: Optional multi-ticker comparison chart
                (e.g. from ComparisonService) to embed on the cover page.
        """
        self._results = results
        self._comparison_figure = comparison_figure

    def export(self) -> bytes:
        """
        Generate the PDF report.

        Returns:
            PDF document as bytes.
        """
        pdf = self._create_pdf()
        self._add_cover(pdf)

        for result in self._results:
            self._add_analysis_page(pdf, result)

        return bytes(pdf.output())

    def _create_pdf(self) -> FPDF:
        """Create a fresh PDF document with the first page already added."""
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        return pdf

    # ------------------------------------------------------------------
    # Cover
    # ------------------------------------------------------------------

    def _add_cover(self, pdf: FPDF) -> None:
        """Render the cover page: title, date, tickers, badges, comparison chart."""
        draw_title(pdf, "Stock Analysis Report")

        pdf.set_font("Arial", "", 10)
        pdf.cell(
            0,
            7,
            text=f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.cell(
            0,
            7,
            text=f"Tickers: {', '.join(result.ticker for result in self._results)}",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        self._add_indicator_badge(pdf)
        self._add_feature_badge(pdf)
        pdf.ln(6)

        self._add_comparison_chart(pdf)

    def _add_indicator_badge(self, pdf: FPDF) -> None:
        """Render the 'Indicators: ...' line, using the union across all results."""
        active = sorted(
            {
                indicator
                for result in self._results
                for indicator in result.active_indicators
            }
        )
        labels = [_INDICATOR_LABELS.get(key, key) for key in active]
        draw_badges(pdf, "Indicators", labels)

    def _add_feature_badge(self, pdf: FPDF) -> None:
        """Render the 'Includes: ...' line for optional sections that are present."""
        features = []
        if any(result.financial_statements for result in self._results):
            features.append("Financial Statements")
        if any(result.backtest_result for result in self._results):
            features.append("Backtest")
        draw_badges(pdf, "Includes", features)

    def _add_comparison_chart(self, pdf: FPDF) -> None:
        """Render the multi-ticker comparison chart on the cover, if provided."""
        if self._comparison_figure is None:
            return

        draw_section_header(pdf, "Relative Performance Comparison")
        image_path = self._save_temp_image(
            self._comparison_figure.to_image(format="png")
        )
        draw_image(pdf, image_path)

    # ------------------------------------------------------------------
    # Per-ticker page
    # ------------------------------------------------------------------

    def _add_analysis_page(self, pdf: FPDF, result: AnalysisResult) -> None:
        """Render one ticker's full section: banner through chart."""
        pdf.add_page()
        draw_banner(pdf, result.ticker)

        self._add_key_statistics(pdf, result)
        self._add_historical_range(pdf, result)
        self._add_fundamentals(pdf, result)
        self._add_financial_statements(pdf, result)
        self._add_commentary(pdf, result)
        self._add_backtest(pdf, result)
        self._add_chart(pdf, result)

    def _add_key_statistics(self, pdf: FPDF, result: AnalysisResult) -> None:
        """Render the latest indicator snapshot (Close, RSI, MACD, EMAs, ...)."""
        draw_section_header(pdf, "Key Statistics")
        rows = self._build_key_statistics_rows(result)
        if rows:
            draw_key_value_table(pdf, rows)
        pdf.ln(4)

    def _add_historical_range(self, pdf: FPDF, result: AnalysisResult) -> None:
        """Render the period high/low table from Statistics."""
        draw_section_header(pdf, "Historical Range")
        draw_key_value_table(pdf, self._build_range_rows(result.statistics))
        pdf.ln(4)

    def _add_fundamentals(self, pdf: FPDF, result: AnalysisResult) -> None:
        """Render the company fundamentals table, if fetched."""
        if result.fundamentals is None:
            return

        draw_section_header(pdf, "Fundamental Data")
        draw_key_value_table(pdf, self._build_fundamentals_rows(result.fundamentals))
        pdf.ln(4)

    def _add_financial_statements(self, pdf: FPDF, result: AnalysisResult) -> None:
        """Render income statement, balance sheet, and cash flow, if fetched."""
        statements = result.financial_statements
        if statements is None:
            return

        self._add_statement_table(
            pdf, "Income Statement (P&L)", statements.income_statement
        )
        self._add_statement_table(pdf, "Balance Sheet", statements.balance_sheet)
        self._add_statement_table(
            pdf, "Cash Flow Statement", statements.cash_flow_statement
        )

    def _add_statement_table(
        self,
        pdf: FPDF,
        title: str,
        statement: FinancialStatement | None,
    ) -> None:
        """Render one financial statement as a multi-period table."""
        if statement is None:
            return

        rows = [(row.label, *row.values) for row in statement.rows]
        draw_financial_table(pdf, title, rows, statement.periods)

    def _add_commentary(self, pdf: FPDF, result: AnalysisResult) -> None:
        """Render the plain-English technical commentary paragraph."""
        draw_section_header(pdf, "Technical Commentary")
        commentary = TrendCommentator(result).generate()
        draw_paragraph(pdf, commentary)

    def _add_backtest(self, pdf: FPDF, result: AnalysisResult) -> None:
        """Render the backtest KPI grid and trade log, if a backtest ran."""
        backtest = result.backtest_result
        draw_section_header(pdf, "Backtest Results")

        if backtest is None:
            pdf.set_font("Arial", "I", 9)
            pdf.cell(
                0,
                6,
                text="  Backtest was not run for this ticker.",
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.ln(3)
            return

        self._add_backtest_kpis(pdf, backtest)
        draw_trade_log(pdf, backtest.trades)

    def _add_backtest_kpis(self, pdf: FPDF, backtest: BacktestResult) -> None:
        """Render the two backtest KPI rows (returns/risk, then capital)."""
        buy_hold = backtest.buy_hold_return or 0.0
        alpha = backtest.total_return - buy_hold

        draw_backtest_kpis(
            pdf,
            [
                (
                    "Strategy Return",
                    f"{backtest.total_return:+.2f}%",
                    backtest.total_return >= 0,
                ),
                ("Buy & Hold", f"{buy_hold:+.2f}%", buy_hold >= 0),
                ("Alpha", f"{alpha:+.2f}%", alpha >= 0),
                (
                    "Max Drawdown",
                    f"{backtest.max_drawdown:.2f}%",
                    backtest.max_drawdown >= -5,
                ),
            ],
        )
        pdf.ln(1)

        starting_value, final_value = self._equity_endpoints(backtest.equity_curve)
        draw_backtest_kpis(
            pdf,
            [
                ("Starting Value", f"${starting_value:,.2f}", None),
                ("Final Value", f"${final_value:,.2f}", final_value >= starting_value),
                (
                    "Sharpe Ratio",
                    f"{backtest.sharpe_ratio:.2f}",
                    backtest.sharpe_ratio >= 1,
                ),
                ("Win Rate", f"{backtest.win_rate:.1f}%", backtest.win_rate >= 50),
            ],
        )
        pdf.ln(4)

    def _equity_endpoints(self, equity_curve: pd.DataFrame) -> tuple[float, float]:
        """
        Get the first and last portfolio values from the equity curve.

        The first value approximates starting capital: BacktestResult
        doesn't carry the original initial_capital directly, but the
        engine records equity from day one, before any trade could
        typically have moved it.
        """
        if equity_curve is None or equity_curve.empty:
            return 0.0, 0.0

        portfolio = equity_curve["Portfolio"]
        return float(portfolio.iloc[0]), float(portfolio.iloc[-1])

    def _add_chart(self, pdf: FPDF, result: AnalysisResult) -> None:
        """Render the technical chart as an embedded PNG."""
        draw_section_header(pdf, "Technical Chart")

        figure = TechnicalChart(result).build()
        image_path = self._save_temp_image(figure.to_image(format="png"))
        draw_image(pdf, image_path)

    # ------------------------------------------------------------------
    # Row builders
    # ------------------------------------------------------------------

    def _build_key_statistics_rows(
        self, result: AnalysisResult
    ) -> list[tuple[str, str]]:
        """Build the latest-snapshot rows (Close, period return, active indicators)."""
        data = result.indicators
        if data.empty:
            return []

        last = data.iloc[-1]
        rows: list[tuple[str, str]] = []

        close = last.get("Close")
        if pd.notna(close):
            rows.append(("Latest Close", f"${close:.2f}"))

        first_close = data["Close"].iloc[0]
        if pd.notna(first_close) and first_close:
            period_return = ((close - first_close) / first_close) * 100
            rows.append(("Period Return", f"{period_return:+.2f}%"))

        rows.extend(self._indicator_snapshot_rows(result.active_indicators, last))
        return rows

    def _indicator_snapshot_rows(
        self,
        active_indicators: list[str],
        last: pd.Series,
    ) -> list[tuple[str, str]]:
        """Build one row per active indicator with its most recent value."""
        specs = [
            ("rsi", "RSI", "RSI (14)", "{:.1f}"),
            ("macd", "MACD", "MACD", "{:.3f}"),
            ("ema20", "EMA20", "EMA 20", "${:.2f}"),
            ("ema50", "EMA50", "EMA 50", "${:.2f}"),
            ("ema200", "EMA200", "EMA 200", "${:.2f}"),
            ("atr", "ATR", "ATR (14)", "{:.2f}"),
            ("stochastic", "Stoch_K", "Stoch %K", "{:.1f}"),
        ]

        rows: list[tuple[str, str]] = []
        for indicator_key, column, label, fmt in specs:
            if indicator_key not in active_indicators or column not in last.index:
                continue
            value = last.get(column)
            if pd.notna(value):
                rows.append((label, fmt.format(value)))

        if "bollinger" in active_indicators and "Bollinger_Upper" in last.index:
            upper, lower = last.get("Bollinger_Upper"), last.get("Bollinger_Lower")
            if pd.notna(upper) and pd.notna(lower):
                rows.append(("BB Upper", f"${upper:.2f}"))
                rows.append(("BB Lower", f"${lower:.2f}"))

        return rows

    def _build_range_rows(self, stats: Statistics) -> list[tuple[str, str]]:
        """Build the historical high/low range rows from Statistics."""
        return [
            ("Period High", f"${stats.period_high:.2f}"),
            ("High Date", stats.period_high_date.strftime("%Y-%m-%d")),
            ("Period Low", f"${stats.period_low:.2f}"),
            ("Low Date", stats.period_low_date.strftime("%Y-%m-%d")),
            ("% From High", f"{stats.pct_from_high:+.2f}%"),
            ("% From Low", f"{stats.pct_from_low:+.2f}%"),
        ]

    def _build_fundamentals_rows(
        self, fundamentals: Fundamentals
    ) -> list[tuple[str, str]]:
        """Build the company fundamentals rows."""
        return [
            (
                "P/E Ratio",
                f"{fundamentals.pe_ratio:.2f}" if fundamentals.pe_ratio else "N/A",
            ),
            ("Market Cap", self._format_large_number(fundamentals.market_cap)),
            (
                "52W High",
                f"${fundamentals.w52_high:.2f}" if fundamentals.w52_high else "N/A",
            ),
            (
                "52W Low",
                f"${fundamentals.w52_low:.2f}" if fundamentals.w52_low else "N/A",
            ),
            (
                "Div Yield",
                (
                    f"{fundamentals.dividend_yield * 100:.2f}%"
                    if fundamentals.dividend_yield
                    else "N/A"
                ),
            ),
            ("Beta", f"{fundamentals.beta:.2f}" if fundamentals.beta else "N/A"),
            ("EPS", f"${fundamentals.eps:.2f}" if fundamentals.eps else "N/A"),
            ("Sector", fundamentals.sector or "N/A"),
            ("Industry", fundamentals.industry or "N/A"),
            ("Revenue", self._format_large_number(fundamentals.revenue)),
        ]

    def _format_large_number(self, value: float | int | None) -> str:
        """Format a large dollar figure with T/B/M suffixes."""
        if value is None:
            return "N/A"
        if value >= 1e12:
            return f"${value / 1e12:.2f}T"
        if value >= 1e9:
            return f"${value / 1e9:.2f}B"
        if value >= 1e6:
            return f"${value / 1e6:.2f}M"
        return f"${value:,.0f}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _save_temp_image(self, data: bytes) -> str:
        """Save chart image bytes to a temp file, since FPDF requires a path."""
        file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        file.write(data)
        file.close()
        return file.name
