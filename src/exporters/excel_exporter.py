# Import standard library packages.
import os

# Import third party packages.
import pandas as pd

# Import local packages.
from src.models.analysis_result import AnalysisResult
from src.models.financial_statements import FinancialStatement
from src.models.signal import Signal

OUTPUT_DIR = "outputs/excels"


class ExcelExporter:
    """
    Exports a single AnalysisResult to a multi-sheet Excel workbook.

    Each section of AnalysisResult (statistics, raw data, indicators,
    signals, fundamentals, financial statements, backtest results) is
    written to its own sheet, only when that data is present.
    """

    def export_excel(self, result: AnalysisResult) -> str:
        """
        Write an AnalysisResult to an Excel file.

        Args:
            result: The analysis result to export.

        Returns:
            The path of the written Excel file.
        """
        file_path = self._build_file_path(result.ticker)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            self._write_summary_sheet(writer, result)
            self._write_raw_data_sheet(writer, result)
            self._write_indicators_sheet(writer, result)
            self._write_signals_sheet(writer, result)
            self._write_fundamentals_sheet(writer, result)
            self._write_financial_statement_sheets(writer, result)
            self._write_backtest_sheets(writer, result)

        return file_path

    def _build_file_path(self, ticker: str) -> str:
        """Build the destination path for a ticker's workbook."""
        return os.path.join(OUTPUT_DIR, f"{ticker}_analysis.xlsx")

    def _write_summary_sheet(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """Write period high/low and current price stats to a Summary sheet."""
        stats = result.statistics
        summary = pd.DataFrame(
            [
                {
                    "Ticker": result.ticker,
                    "Period High": stats.period_high,
                    "High Date": stats.period_high_date,
                    "Period Low": stats.period_low,
                    "Low Date": stats.period_low_date,
                    "Current Close": stats.current_close,
                    "% From High": stats.pct_from_high,
                    "% From Low": stats.pct_from_low,
                }
            ]
        )
        summary.to_excel(writer, sheet_name="Summary", index=False)

    def _write_raw_data_sheet(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """Write the raw OHLCV data to its own sheet."""
        result.raw_data.to_excel(writer, sheet_name="Raw Data")

    def _write_indicators_sheet(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """Write OHLCV + calculated indicator columns to their own sheet."""
        result.indicators.to_excel(writer, sheet_name="Indicators")

    def _write_signals_sheet(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """Write detected trading signals to their own sheet, if any exist."""
        if not result.signals:
            return

        signals_df = self._signals_to_frame(result.signals)
        signals_df.to_excel(writer, sheet_name="Signals", index=False)

    def _signals_to_frame(self, signals: list[Signal]) -> pd.DataFrame:
        """Convert a list of Signal models into a flat DataFrame."""
        return pd.DataFrame(
            [
                {
                    "Date": signal.date,
                    "Type": signal.signal_type.value,
                    "Price": signal.price,
                    "Reason": signal.reason,
                }
                for signal in signals
            ]
        )

    def _write_fundamentals_sheet(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """Write company fundamentals to their own sheet, if requested."""
        if result.fundamentals is None:
            return

        fundamentals_df = pd.DataFrame([result.fundamentals.model_dump()])
        fundamentals_df.to_excel(writer, sheet_name="Fundamentals", index=False)

    def _write_financial_statement_sheets(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """Write income statement, balance sheet, and cash flow, if requested."""
        statements = result.financial_statements
        if statements is None:
            return

        self._write_statement(writer, "Income Statement", statements.income_statement)
        self._write_statement(writer, "Balance Sheet", statements.balance_sheet)
        self._write_statement(writer, "Cash Flow", statements.cash_flow_statement)

    def _write_statement(
        self,
        writer: pd.ExcelWriter,
        sheet_name: str,
        statement: FinancialStatement | None,
    ) -> None:
        """Write a single FinancialStatement to a sheet, if it has data."""
        if statement is None:
            return

        statement_df = pd.DataFrame(
            [row.values for row in statement.rows],
            index=[row.label for row in statement.rows],
            columns=statement.periods,
        )
        statement_df.to_excel(writer, sheet_name=sheet_name)

    def _write_backtest_sheets(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """Write backtest metrics, trades, and equity curve, if requested."""
        backtest = result.backtest_result
        if backtest is None:
            return

        self._write_backtest_summary(writer, backtest)
        self._write_backtest_trades(writer, backtest)
        backtest.equity_curve.to_excel(writer, sheet_name="Equity Curve")

    def _write_backtest_summary(self, writer: pd.ExcelWriter, backtest) -> None:
        """Write top-line backtest metrics to a summary sheet."""
        summary = pd.DataFrame(
            [
                {
                    "Total Return %": backtest.total_return,
                    "Buy & Hold Return %": backtest.buy_hold_return,
                    "Sharpe Ratio": backtest.sharpe_ratio,
                    "Max Drawdown %": backtest.max_drawdown,
                    "Win Rate %": backtest.win_rate,
                    "# Trades": backtest.num_trades,
                }
            ]
        )
        summary.to_excel(writer, sheet_name="Backtest Summary", index=False)

    def _write_backtest_trades(self, writer: pd.ExcelWriter, backtest) -> None:
        """Write the list of completed trades to their own sheet, if any."""
        if not backtest.trades:
            return

        trades_df = pd.DataFrame([trade.model_dump() for trade in backtest.trades])
        trades_df.to_excel(writer, sheet_name="Trades", index=False)
