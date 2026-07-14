from __future__ import annotations

from fpdf import FPDF

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

_HEADER_COLOR = (28, 40, 65)
_SECTION_COLOR = (70, 90, 130)
_ALT_ROW_COLOR = (240, 243, 250)


# ─────────────────────────────────────────────────────────────
# Text helpers
# ─────────────────────────────────────────────────────────────


def sanitize_text(text: str) -> str:
    """
    Replace unicode characters unsupported by FPDF's default fonts.
    """
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# ─────────────────────────────────────────────────────────────
# Headers
# ─────────────────────────────────────────────────────────────


def draw_title(pdf: FPDF, title: str) -> None:
    """
    Draw main report title.
    """
    pdf.set_font("Arial", "B", 20)
    pdf.cell(
        0,
        14,
        text=sanitize_text(title),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )


def draw_section_header(pdf: FPDF, title: str) -> None:
    """
    Draw a section separator.
    """
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(*_SECTION_COLOR)
    pdf.set_text_color(255, 255, 255)

    pdf.cell(
        0,
        8,
        text=f"  {sanitize_text(title)}",
        fill=True,
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


def draw_banner(pdf: FPDF, text: str) -> None:
    """
    Draw ticker banner.
    """
    pdf.set_fill_color(*_HEADER_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 15)

    pdf.cell(
        0,
        12,
        text=f"  {sanitize_text(text)}",
        fill=True,
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)


# ─────────────────────────────────────────────────────────────
# Tables
# ─────────────────────────────────────────────────────────────


def draw_key_value_table(
    pdf: FPDF,
    rows: list[tuple[str, str]],
    column_width: float = 45,
) -> None:
    """
    Draw a compact two-column key/value table.

    Example:
        [
            ("Latest Close", "$120.50"),
            ("RSI", "55.4")
        ]
    """

    pdf.set_font("Arial", "", 9)

    for index in range(0, len(rows), 2):
        left = rows[index]
        right = rows[index + 1] if index + 1 < len(rows) else ("", "")

        for label, value in (left, right):
            pdf.set_font("Arial", "B", 9)
            pdf.cell(
                column_width,
                6,
                text=sanitize_text(label),
                border=1,
                fill=False,
            )

            pdf.set_font("Arial", "", 9)
            pdf.cell(
                column_width,
                6,
                text=sanitize_text(value),
                border=1,
            )

        pdf.ln()


def draw_table(
    pdf: FPDF,
    headers: list[str],
    rows: list[list[str]],
    widths: list[float],
) -> None:
    """
    Generic table renderer.
    """

    # Header
    pdf.set_fill_color(*_HEADER_COLOR)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)

    for width, header in zip(widths, headers):
        pdf.cell(
            width,
            7,
            text=sanitize_text(header),
            border=1,
            fill=True,
            align="C",
        )

    pdf.ln()

    # Rows
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 9)

    for index, row in enumerate(rows):

        if index % 2 == 0:
            pdf.set_fill_color(*_ALT_ROW_COLOR)
        else:
            pdf.set_fill_color(255, 255, 255)

        for width, value in zip(widths, row):
            pdf.cell(
                width,
                6,
                text=sanitize_text(str(value)),
                border=1,
                fill=True,
            )

        pdf.ln()


# ─────────────────────────────────────────────────────────────
# Charts
# ─────────────────────────────────────────────────────────────


def draw_image(
    pdf: FPDF,
    image_path: str,
    width: float = 185,
) -> None:
    """
    Add a chart image to the PDF.
    """

    pdf.image(
        image_path,
        x=10,
        w=width,
    )

    pdf.ln(5)


# ─────────────────────────────────────────────────────────────
# Paragraphs
# ─────────────────────────────────────────────────────────────


def draw_paragraph(
    pdf: FPDF,
    text: str,
) -> None:
    """
    Add wrapped text.
    """

    pdf.set_font("Arial", "", 10)

    pdf.multi_cell(
        0,
        6,
        text=sanitize_text(text),
    )

    pdf.ln(3)
