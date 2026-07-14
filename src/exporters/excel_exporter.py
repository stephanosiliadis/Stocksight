# Import standard library packages.
from io import BytesIO

# Import third party packages.
import pandas as pd

# Import local packages.
from src.models.analysis_result import AnalysisResult
from src.models.financial_statements import FinancialStatement
from src.models.signal import Signal


class ExcelExporter:
    """
    Exports an AnalysisResult into an Excel workbook.

    The generated workbook is returned as bytes so it can be directly
    downloaded by a frontend (e.g. Streamlit) without requiring temporary
    files on disk.
    """

    def export_excel(
        self,
        result: AnalysisResult,
    ) -> bytes:
        """
        Convert an AnalysisResult into an Excel workbook.

        Args:
            result: Complete analysis output to export.

        Returns:
            Excel workbook content as bytes.
        """
        buffer = BytesIO()

        with pd.ExcelWriter(
            buffer,
            engine="openpyxl",
        ) as writer:
            self._write_summary_sheet(writer, result)
            self._write_raw_data_sheet(writer, result)
            self._write_indicators_sheet(writer, result)
            self._write_signals_sheet(writer, result)
            self._write_fundamentals_sheet(writer, result)
            self._write_financial_statement_sheets(writer, result)
            self._write_backtest_sheets(writer, result)

        buffer.seek(0)

        return buffer.getvalue()

    def _write_summary_sheet(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """
        Write general analysis information and price statistics.
        """
        stats = result.statistics

        summary = pd.DataFrame(
            [
                {
                    "Ticker": result.ticker,
                    "Active Indicators": ", ".join(result.active_indicators),
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

        summary.to_excel(
            writer,
            sheet_name="Summary",
            index=False,
        )

    def _write_raw_data_sheet(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """
        Write raw OHLCV market data.
        """
        result.raw_data.to_excel(
            writer,
            sheet_name="Raw Data",
        )

    def _write_indicators_sheet(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """
        Write OHLCV data with calculated indicators.
        """
        result.indicators.to_excel(
            writer,
            sheet_name="Indicators",
        )

    def _write_signals_sheet(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """
        Write generated trading signals.
        """
        if not result.signals:
            return

        signals_df = self._signals_to_dataframe(result.signals)

        signals_df.to_excel(
            writer,
            sheet_name="Signals",
            index=False,
        )

    def _signals_to_dataframe(
        self,
        signals: list[Signal],
    ) -> pd.DataFrame:
        """
        Convert Signal models into a tabular representation.
        """
        return pd.DataFrame(
            [
                {
                    "Ticker": signal.ticker,
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
        """
        Write company fundamental information.
        """
        if result.fundamentals is None:
            return

        fundamentals_df = pd.DataFrame([result.fundamentals.model_dump()])

        fundamentals_df.to_excel(
            writer,
            sheet_name="Fundamentals",
            index=False,
        )

    def _write_financial_statement_sheets(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """
        Write financial statements if available.
        """
        statements = result.financial_statements

        if statements is None:
            return

        self._write_statement(
            writer,
            "Income Statement",
            statements.income_statement,
        )

        self._write_statement(
            writer,
            "Balance Sheet",
            statements.balance_sheet,
        )

        self._write_statement(
            writer,
            "Cash Flow",
            statements.cash_flow_statement,
        )

    def _write_statement(
        self,
        writer: pd.ExcelWriter,
        sheet_name: str,
        statement: FinancialStatement | None,
    ) -> None:
        """
        Write a single financial statement.
        """
        if statement is None:
            return

        statement_df = pd.DataFrame(
            [row.values for row in statement.rows],
            index=[row.label for row in statement.rows],
            columns=statement.periods,
        )

        statement_df.to_excel(
            writer,
            sheet_name=sheet_name,
        )

    def _write_backtest_sheets(
        self,
        writer: pd.ExcelWriter,
        result: AnalysisResult,
    ) -> None:
        """
        Write backtesting results.
        """
        backtest = result.backtest_result

        if backtest is None:
            return

        self._write_backtest_summary(
            writer,
            backtest,
        )

        self._write_backtest_trades(
            writer,
            backtest,
        )

        backtest.equity_curve.to_excel(
            writer,
            sheet_name="Equity Curve",
        )

    def _write_backtest_summary(
        self,
        writer: pd.ExcelWriter,
        backtest,
    ) -> None:
        """
        Write backtest performance metrics.
        """
        summary = pd.DataFrame(
            [
                {
                    "Total Return %": backtest.total_return,
                    "Buy & Hold Return %": backtest.buy_hold_return,
                    "Sharpe Ratio": backtest.sharpe_ratio,
                    "Max Drawdown %": backtest.max_drawdown,
                    "Win Rate %": backtest.win_rate,
                    "Number of Trades": backtest.num_trades,
                }
            ]
        )

        summary.to_excel(
            writer,
            sheet_name="Backtest Summary",
            index=False,
        )

    def _write_backtest_trades(
        self,
        writer: pd.ExcelWriter,
        backtest,
    ) -> None:
        """
        Write completed trades.
        """
        if not backtest.trades:
            return

        trades_df = pd.DataFrame([trade.model_dump() for trade in backtest.trades])

        trades_df.to_excel(
            writer,
            sheet_name="Trades",
            index=False,
        )
