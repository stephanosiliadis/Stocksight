from __future__ import annotations

from datetime import datetime

from fpdf import FPDF

from src.models.analysis_result import AnalysisResult
from src.reporting.pdf_components import (
    draw_banner,
    draw_image,
    draw_key_value_table,
    draw_paragraph,
    draw_section_header,
    draw_title,
)
from src.reporting.trend_commentator import TrendCommentator
from src.visualization.technical_chart import TechnicalChart


class PDFExporter:
    """
    Generates PDF reports from analysis results.

    The exporter returns PDF bytes so callers can:
        - save the file
        - stream it through Streamlit
        - attach it elsewhere

    It does not handle UI or filesystem operations.
    """

    def __init__(
        self,
        results: list[AnalysisResult],
    ) -> None:
        self._results = results

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

    # ------------------------------------------------------------------
    # PDF creation
    # ------------------------------------------------------------------

    def _create_pdf(self) -> FPDF:
        pdf = FPDF()
        pdf.set_auto_page_break(
            auto=True,
            margin=15,
        )
        pdf.add_page()

        return pdf

    # ------------------------------------------------------------------
    # Cover
    # ------------------------------------------------------------------

    def _add_cover(
        self,
        pdf: FPDF,
    ) -> None:
        draw_title(
            pdf,
            "Stock Analysis Report",
        )

        pdf.set_font(
            "Arial",
            "",
            10,
        )

        pdf.cell(
            0,
            7,
            text=f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        tickers = ", ".join(result.ticker for result in self._results)

        pdf.cell(
            0,
            7,
            text=f"Tickers: {tickers}",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        pdf.ln(10)

    # ------------------------------------------------------------------
    # Analysis page
    # ------------------------------------------------------------------

    def _add_analysis_page(
        self,
        pdf: FPDF,
        result: AnalysisResult,
    ) -> None:

        pdf.add_page()

        draw_banner(
            pdf,
            result.ticker,
        )

        self._add_statistics(
            pdf,
            result,
        )

        self._add_commentary(
            pdf,
            result,
        )

        self._add_chart(
            pdf,
            result,
        )

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _add_statistics(
        self,
        pdf: FPDF,
        result: AnalysisResult,
    ) -> None:

        draw_section_header(
            pdf,
            "Key Statistics",
        )

        rows = self._build_statistics(
            result,
        )

        if rows:
            draw_key_value_table(
                pdf,
                rows,
            )

        pdf.ln(5)

    def _add_commentary(
        self,
        pdf: FPDF,
        result: AnalysisResult,
    ) -> None:

        draw_section_header(
            pdf,
            "Technical Commentary",
        )

        commentary = TrendCommentator(
            result,
        ).generate()

        draw_paragraph(
            pdf,
            commentary,
        )

    def _add_chart(
        self,
        pdf: FPDF,
        result: AnalysisResult,
    ) -> None:

        draw_section_header(
            pdf,
            "Technical Chart",
        )

        chart = TechnicalChart(
            result,
        )

        figure = chart.build()

        image_bytes = figure.to_image(
            format="png",
        )

        image_path = self._save_temp_image(
            image_bytes,
        )

        draw_image(
            pdf,
            image_path,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_statistics(
        self,
        result: AnalysisResult,
    ) -> list[tuple[str, str]]:

        data = result.indicators

        if data.empty:
            return []

        last = data.iloc[-1]

        rows: list[tuple[str, str]] = []

        close = last.get("Close")

        if close is not None:
            rows.append(
                (
                    "Latest Close",
                    f"${close:.2f}",
                )
            )

        if "RSI" in data.columns:
            rsi = last.get("RSI")

            if rsi is not None:
                rows.append(
                    (
                        "RSI",
                        f"{rsi:.1f}",
                    )
                )

        return rows

    def _save_temp_image(
        self,
        data: bytes,
    ) -> str:
        """
        Save chart temporarily for FPDF.

        FPDF requires a path for images.
        """

        import tempfile

        file = tempfile.NamedTemporaryFile(
            suffix=".png",
            delete=False,
        )

        file.write(data)
        file.close()

        return file.name
