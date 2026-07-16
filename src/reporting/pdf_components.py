# Import third party packages.
from fpdf import FPDF

# Characters outside latin-1 that commonly appear in generated text. FPDF's
# core "Arial" font only supports latin-1, so anything routed through
# sanitize_text() (all draw_* functions below do this internally) needs
# these swapped out first.
_UNICODE_REPLACEMENTS = str.maketrans(
    {
        "\u2014": "-",  # em dash
        "\u2013": "-",  # en dash
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2026": "...",  # ellipsis
    }
)

# Shared color scheme.
_BANNER_RGB = (22, 33, 60)
_SECTION_HEADER_RGB = (70, 90, 130)
_TABLE_HEADER_RGB = (28, 40, 65)
_ALT_ROW_RGB = (240, 243, 250)
_POSITIVE_RGB = (230, 247, 235)
_NEGATIVE_RGB = (253, 235, 235)

# Financial statement rows whose value cells get green/red sign coloring.
_SIGNED_ROW_LABELS = {
    "Net Income",
    "Operating Income",
    "Gross Profit",
    "EBITDA",
    "Free Cash Flow",
    "Operating Cash Flow",
}

PAGE_WIDTH = 190.0  # Usable width on an A4 page with default margins.


def sanitize_text(text: str) -> str:
    """Replace unicode characters fpdf's latin-1 core fonts cannot encode."""
    return text.translate(_UNICODE_REPLACEMENTS)


def draw_title(pdf: FPDF, title: str) -> None:
    """Render the report's main cover title."""
    pdf.set_font("Arial", "B", 20)
    pdf.cell(0, 14, text=sanitize_text(title), align="C", new_x="LMARGIN", new_y="NEXT")


def draw_badges(pdf: FPDF, label: str, items: list[str]) -> None:
    """Render a small italic '<Label>: a, b, c' line. No-op if items is empty."""
    if not items:
        return

    pdf.set_font("Arial", "I", 9)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 6, text=sanitize_text(f"{label}: {', '.join(items)}"), align="C")


def draw_banner(pdf: FPDF, text: str) -> None:
    """Render a dark full-width ticker banner at the top of a page."""
    pdf.set_fill_color(*_BANNER_RGB)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 15)
    pdf.cell(
        0,
        12,
        text=f"  {sanitize_text(text)}",
        new_x="LMARGIN",
        new_y="NEXT",
        fill=True,
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)


def draw_section_header(pdf: FPDF, title: str) -> None:
    """Render a styled section sub-header inside a ticker page."""
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(*_SECTION_HEADER_RGB)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(
        0,
        8,
        text=f"  {sanitize_text(title)}",
        new_x="LMARGIN",
        new_y="NEXT",
        fill=True,
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def draw_paragraph(pdf: FPDF, text: str) -> None:
    """Render a block of body text."""
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, text=sanitize_text(text))
    pdf.ln(4)


def draw_image(pdf: FPDF, image_path: str, width: float = 185.0) -> None:
    """Render a full-width image (chart) at the current position."""
    pdf.image(image_path, x=10, w=width)
    pdf.ln(4)


def draw_key_value_table(
    pdf: FPDF,
    rows: list[tuple[str, str]],
    col_width: float = 45.0,
) -> None:
    """Render (label, value) pairs as a compact two-column-pair table."""
    for index in range(0, len(rows), 2):
        label_1, value_1 = rows[index]
        label_2, value_2 = rows[index + 1] if index + 1 < len(rows) else ("", "")

        pdf.set_font("Arial", "B", 9)
        pdf.cell(col_width, 6, text=sanitize_text(label_1), border=1)
        pdf.set_font("Arial", "", 9)
        pdf.cell(col_width, 6, text=sanitize_text(value_1), border=1)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(col_width, 6, text=sanitize_text(label_2), border=1)
        pdf.set_font("Arial", "", 9)
        pdf.cell(
            col_width,
            6,
            text=sanitize_text(value_2),
            border=1,
            new_x="LMARGIN",
            new_y="NEXT",
        )

    pdf.ln(2)


def draw_financial_table(
    pdf: FPDF,
    title: str,
    rows: list[tuple],
    period_labels: list[str],
) -> None:
    """
    Render a financial statement as a styled multi-period table.

    Args:
        title: Section heading (e.g. "Income Statement (P&L)").
        rows: List of tuples: (label, val_period0, val_period1, ...).
        period_labels: Year/quarter strings for each value column.
    """
    draw_section_header(pdf, title)

    if not rows or not period_labels:
        pdf.set_font("Arial", "I", 9)
        pdf.cell(
            0,
            6,
            text="  Data not available for this ticker.",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(3)
        return

    period_count = min(len(period_labels), 3)
    label_width = 72.0
    value_width = (PAGE_WIDTH - label_width) / period_count

    _draw_financial_header_row(
        pdf, period_labels[:period_count], label_width, value_width
    )

    for index, row in enumerate(rows):
        label = sanitize_text(str(row[0]))
        values = [str(value) for value in row[1 : period_count + 1]]
        _draw_financial_row(pdf, label, values, index, label_width, value_width)

    pdf.ln(4)


def _draw_financial_header_row(
    pdf: FPDF,
    period_labels: list[str],
    label_width: float,
    value_width: float,
) -> None:
    """Render the "Metric | period0 | period1 | ..." header row."""
    pdf.set_fill_color(*_TABLE_HEADER_RGB)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(label_width, 7, text="  Metric", border=1, fill=True)
    for label in period_labels:
        pdf.cell(
            value_width, 7, text=sanitize_text(label), border=1, fill=True, align="C"
        )
    pdf.ln()
    pdf.set_text_color(0, 0, 0)


def _draw_financial_row(
    pdf: FPDF,
    label: str,
    values: list[str],
    index: int,
    label_width: float,
    value_width: float,
) -> None:
    """Render one row of a financial statement table with sign-based coloring."""
    if label in _SIGNED_ROW_LABELS and values:
        pdf.set_fill_color(
            *(_NEGATIVE_RGB if values[0].startswith("-") else _POSITIVE_RGB)
        )
    elif index % 2 == 0:
        pdf.set_fill_color(*_ALT_ROW_RGB)
    else:
        pdf.set_fill_color(255, 255, 255)

    pdf.set_font("Arial", "B", 9)
    pdf.cell(label_width, 6, text=f"  {label}", border=1, fill=True)

    pdf.set_font("Arial", "", 9)
    for value in values:
        (
            pdf.set_text_color(180, 40, 40)
            if value.startswith("-")
            else pdf.set_text_color(0, 0, 0)
        )
        pdf.cell(value_width, 6, text=value, border=1, fill=True, align="R")

    pdf.set_text_color(0, 0, 0)
    pdf.ln()


def draw_backtest_kpis(pdf: FPDF, pairs: list[tuple[str, str, bool | None]]) -> None:
    """
    Render one row of dark KPI cells.

    Args:
        pairs: List of (label, value, is_positive). is_positive controls
            the value's color: green if True, red if False, white if None.
    """
    cell_width = PAGE_WIDTH / len(pairs)

    pdf.set_font("Arial", "B", 7)
    for label, _, _ in pairs:
        pdf.set_fill_color(40, 55, 90)
        pdf.set_text_color(180, 200, 230)
        pdf.cell(cell_width, 5, text=label.upper(), fill=True, align="C")
    pdf.ln()

    pdf.set_font("Arial", "B", 11)
    for _, value, positive in pairs:
        pdf.set_fill_color(50, 65, 105)
        if positive is True:
            pdf.set_text_color(100, 220, 140)
        elif positive is False:
            pdf.set_text_color(240, 100, 100)
        else:
            pdf.set_text_color(255, 255, 255)
        pdf.cell(cell_width, 9, text=value, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)


def draw_trade_log(pdf: FPDF, trades: list) -> None:
    """
    Render the completed round-trip trades table.

    Args:
        trades: List of Trade models (ticker, entry_date, exit_date,
            entry_price, exit_price, pnl, return_pct).
    """
    if not trades:
        pdf.set_font("Arial", "I", 9)
        pdf.cell(0, 6, text="  No trades were executed.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        return

    pdf.set_font("Arial", "B", 10)
    pdf.cell(
        0,
        7,
        text=f"Trade Log  ({len(trades)} entries)",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    col_widths = [26, 26, 26, 26, 30, 26, 30]
    headers = ["Entry Date", "Exit Date", "Entry $", "Exit $", "P&L $", "P&L %", ""]

    pdf.set_fill_color(*_TABLE_HEADER_RGB)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 8)
    for width, header in zip(col_widths, headers):
        pdf.cell(width, 6, text=header, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    for trade in trades:
        _draw_trade_row(pdf, trade, col_widths)


def _draw_trade_row(pdf: FPDF, trade, col_widths: list[float]) -> None:
    """Render a single trade row, colored green/red by P&L sign."""
    is_win = trade.pnl >= 0
    pdf.set_fill_color(*(_POSITIVE_RGB if is_win else _NEGATIVE_RGB))
    pdf.set_text_color(30, 140, 60) if is_win else pdf.set_text_color(180, 40, 40)

    pdf.set_font("Arial", "", 8)
    values = [
        trade.entry_date.strftime("%Y-%m-%d"),
        trade.exit_date.strftime("%Y-%m-%d"),
        f"${trade.entry_price:.2f}",
        f"${trade.exit_price:.2f}",
        f"${trade.pnl:,.2f}",
        f"{trade.return_pct:+.2f}%",
        "",
    ]
    for width, value in zip(col_widths, values):
        pdf.cell(width, 5, text=value, border=1, fill=True, align="R")

    pdf.set_text_color(0, 0, 0)
    pdf.ln()
