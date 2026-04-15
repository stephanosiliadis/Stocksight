import logging
import os
from datetime import datetime

import pandas as pd
from fpdf import FPDF

log = logging.getLogger(__name__)

_INDICATOR_LABELS = {
    "bollinger": "Bollinger Bands",
    "rsi": "RSI (14)",
    "macd": "MACD",
    "ema20": "EMA 20",
    "ema50": "EMA 50",
    "ema200": "EMA 200",
    "volume": "Volume",
    "atr": "ATR (14)",
    "stochastic": "Stochastic Oscillator",
    "signals": "Buy / Sell Signals",
    "support_resistance": "Support & Resistance",
}

# Characters outside latin-1 that commonly appear in generated text.
_UNICODE_REPLACEMENTS = str.maketrans(
    {
        "\u2014": "-",  # em dash  —
        "\u2013": "-",  # en dash  –
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
        "\u2026": "...",  # ellipsis
    }
)


def _sanitize(text: str) -> str:
    """Replace unicode characters that fpdf's latin-1 fonts cannot encode."""
    return text.translate(_UNICODE_REPLACEMENTS)


# ─────────────────────────────────────────────────────────────────────────────
# Commentary
# ─────────────────────────────────────────────────────────────────────────────


def generate_trend_commentary(ticker: str, data: pd.DataFrame, indicators: list) -> str:
    """
    Generate a plain-English technical summary for the most recent data point.
    """
    if data is None or data.empty:
        return "No data available for commentary."

    last = data.iloc[-1]
    lines = []

    # RSI
    if "rsi" in indicators and "RSI" in data.columns:
        rsi_val = last.get("RSI")
        if pd.notna(rsi_val):
            if rsi_val > 70:
                lines.append(
                    f"RSI is overbought at {rsi_val:.1f}, suggesting a potential pullback."
                )
            elif rsi_val < 30:
                lines.append(
                    f"RSI is oversold at {rsi_val:.1f}, suggesting a potential bounce."
                )
            else:
                lines.append(f"RSI is neutral at {rsi_val:.1f}.")

    # Stochastic
    if "stochastic" in indicators and "Stoch_K" in data.columns:
        k_val = last.get("Stoch_K")
        if pd.notna(k_val):
            if k_val > 80:
                lines.append(f"Stochastic %K ({k_val:.1f}) is overbought.")
            elif k_val < 20:
                lines.append(f"Stochastic %K ({k_val:.1f}) is oversold.")

    # MACD
    if "macd" in indicators and "MACD" in data.columns:
        macd_val = last.get("MACD")
        macd_sig = last.get("MACD_Signal")
        macd_hist = last.get("MACD_Histogram")
        if pd.notna(macd_val) and pd.notna(macd_sig):
            direction = "above" if macd_val > macd_sig else "below"
            sentiment = "bullish" if macd_val > macd_sig else "bearish"
            lines.append(
                f"MACD ({macd_val:.2f}) is {direction} the signal line "
                f"({macd_sig:.2f}), indicating {sentiment} momentum."
            )
        if pd.notna(macd_hist):
            lines.append(
                "Histogram is positive — momentum increasing."
                if macd_hist > 0
                else "Histogram is negative — momentum decreasing."
            )

    # EMA 50 vs 200 (Golden / Death cross)
    if all(k in indicators for k in ("ema50", "ema200")) and all(
        c in data.columns for c in ("EMA50", "EMA200")
    ):
        ema50 = last.get("EMA50")
        ema200 = last.get("EMA200")
        if pd.notna(ema50) and pd.notna(ema200):
            if ema50 > ema200:
                lines.append(
                    f"Golden Cross active: EMA50 ({ema50:.2f}) is above EMA200 "
                    f"({ema200:.2f}) — long-term bullish structure."
                )
            else:
                lines.append(
                    f"Death Cross active: EMA50 ({ema50:.2f}) is below EMA200 "
                    f"({ema200:.2f}) — long-term bearish structure."
                )

    # Price vs EMA50
    if "ema50" in indicators and "EMA50" in data.columns:
        ema50 = last.get("EMA50")
        close = last.get("Close")
        if pd.notna(ema50) and pd.notna(close):
            pos = "above" if close > ema50 else "below"
            lines.append(f"Price ({close:.2f}) is {pos} EMA50 ({ema50:.2f}).")

    # Bollinger Bands
    if "bollinger" in indicators and "Bollinger_Upper" in data.columns:
        close = last.get("Close")
        bb_upper = last.get("Bollinger_Upper")
        bb_lower = last.get("Bollinger_Lower")
        if pd.notna(close) and pd.notna(bb_upper) and pd.notna(bb_lower):
            if close > bb_upper:
                lines.append(
                    "Price has broken above the upper Bollinger Band — potentially overbought."
                )
            elif close < bb_lower:
                lines.append(
                    "Price has broken below the lower Bollinger Band — potentially oversold."
                )
            else:
                lines.append("Price is trading within the Bollinger Bands.")

    # ATR / Volatility
    if "atr" in indicators and "ATR" in data.columns:
        atr_val = last.get("ATR")
        close = last.get("Close")
        if pd.notna(atr_val) and pd.notna(close) and close > 0:
            pct = (atr_val / close) * 100
            vol_label = "high" if pct > 3 else ("moderate" if pct > 1.5 else "low")
            lines.append(
                f"ATR is {atr_val:.2f} ({pct:.1f}% of price), indicating {vol_label} volatility."
            )

    return "  ".join(lines) if lines else "Insufficient indicator data for commentary."


# ─────────────────────────────────────────────────────────────────────────────
# Summary table builder
# ─────────────────────────────────────────────────────────────────────────────


def _build_summary_rows(data: pd.DataFrame, indicators: list) -> list[tuple[str, str]]:
    """Return a list of (label, value) pairs for the key-stats table."""
    if data is None or data.empty:
        return []

    last = data.iloc[-1]
    rows = []

    close = last.get("Close")
    if pd.notna(close):
        rows.append(("Latest Close", f"${close:.2f}"))

    pct = (
        (data["Close"].iloc[-1] - data["Close"].iloc[0]) / data["Close"].iloc[0]
    ) * 100
    rows.append(("Period Return", f"{pct:+.2f}%"))

    if "rsi" in indicators and "RSI" in data.columns:
        v = last.get("RSI")
        if pd.notna(v):
            rows.append(("RSI (14)", f"{v:.1f}"))

    if "macd" in indicators and "MACD" in data.columns:
        v = last.get("MACD")
        if pd.notna(v):
            rows.append(("MACD", f"{v:.3f}"))

    if "ema20" in indicators and "EMA20" in data.columns:
        v = last.get("EMA20")
        if pd.notna(v):
            rows.append(("EMA 20", f"${v:.2f}"))

    if "ema50" in indicators and "EMA50" in data.columns:
        v = last.get("EMA50")
        if pd.notna(v):
            rows.append(("EMA 50", f"${v:.2f}"))

    if "ema200" in indicators and "EMA200" in data.columns:
        v = last.get("EMA200")
        if pd.notna(v):
            rows.append(("EMA 200", f"${v:.2f}"))

    if "atr" in indicators and "ATR" in data.columns:
        v = last.get("ATR")
        if pd.notna(v):
            rows.append(("ATR (14)", f"{v:.2f}"))

    if "stochastic" in indicators and "Stoch_K" in data.columns:
        v = last.get("Stoch_K")
        if pd.notna(v):
            rows.append(("Stoch %K", f"{v:.1f}"))

    if "bollinger" in indicators and "Bollinger_Upper" in data.columns:
        u = last.get("Bollinger_Upper")
        l = last.get("Bollinger_Lower")
        if pd.notna(u) and pd.notna(l):
            rows.append(("BB Upper", f"${u:.2f}"))
            rows.append(("BB Lower", f"${l:.2f}"))

    return rows


def _build_fundamentals_rows(fund: dict) -> list[tuple[str, str]]:
    """Return a list of (label, value) pairs for the fundamentals table."""

    def fmt_large(n):
        if n is None:
            return "N/A"
        if n >= 1e12:
            return f"${n / 1e12:.2f}T"
        if n >= 1e9:
            return f"${n / 1e9:.2f}B"
        if n >= 1e6:
            return f"${n / 1e6:.2f}M"
        return f"${n:,.0f}"

    return [
        ("P/E Ratio", f"{fund['pe_ratio']:.2f}" if fund.get("pe_ratio") else "N/A"),
        ("Market Cap", fmt_large(fund.get("market_cap"))),
        ("52W High", f"${fund['52w_high']:.2f}" if fund.get("52w_high") else "N/A"),
        ("52W Low", f"${fund['52w_low']:.2f}" if fund.get("52w_low") else "N/A"),
        (
            "Div Yield",
            (
                f"{fund['dividend_yield'] * 100:.2f}%"
                if fund.get("dividend_yield")
                else "N/A"
            ),
        ),
        ("Beta", f"{fund['beta']:.2f}" if fund.get("beta") else "N/A"),
        ("EPS", f"${fund['eps']:.2f}" if fund.get("eps") else "N/A"),
        ("Sector", _sanitize(fund.get("sector") or "N/A")),
        ("Industry", _sanitize(fund.get("industry") or "N/A")),
        ("Revenue", fmt_large(fund.get("revenue"))),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# PDF helpers — existing two-column layout
# ─────────────────────────────────────────────────────────────────────────────


def _draw_two_col_table(pdf: FPDF, rows: list[tuple[str, str]], col_w: float = 45.0):
    """
    Render a list of (label, value) pairs as a compact two-column-pair table.
    Each printed row has: [label][value][label][value].
    """
    for i in range(0, len(rows), 2):
        lbl1, val1 = rows[i]
        lbl2, val2 = rows[i + 1] if i + 1 < len(rows) else ("", "")

        pdf.set_font("Arial", "B", 9)
        pdf.cell(col_w, 6, text=lbl1, border=1)
        pdf.set_font("Arial", "", 9)
        pdf.cell(col_w, 6, text=val1, border=1)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(col_w, 6, text=lbl2, border=1)
        pdf.set_font("Arial", "", 9)
        pdf.cell(col_w, 6, text=val2, border=1, new_x="LMARGIN", new_y="NEXT")


# ─────────────────────────────────────────────────────────────────────────────
# PDF helpers — financial statement multi-period table
# ─────────────────────────────────────────────────────────────────────────────

# Colour scheme
_HDR_R, _HDR_G, _HDR_B = 28, 40, 65  # dark navy header
_ALT_R, _ALT_G, _ALT_B = 240, 243, 250  # light lavender alt rows
_POS_R, _POS_G, _POS_B = 230, 247, 235  # subtle green for positive P&L
_NEG_R, _NEG_G, _NEG_B = 253, 235, 235  # subtle red for negative P&L

# Rows whose values should be coloured green/red based on sign
_SIGNED_ROWS = {
    "Net Income",
    "Operating Income",
    "Gross Profit",
    "EBITDA",
    "Free Cash Flow",
    "Operating Cash Flow",
}


def _draw_section_header(pdf: FPDF, title: str) -> None:
    """Render a styled section sub-header inside a ticker page."""
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(70, 90, 130)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 8, text=f"  {title}", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(1)


def _draw_financial_table(
    pdf: FPDF,
    title: str,
    rows: list[tuple],
    period_labels: list[str],
) -> None:
    """
    Render a financial statement as a styled multi-period table.

    Args:
        title:          Section heading (e.g. "Income Statement (P&L)").
        rows:           List of tuples: (label, val_period0, val_period1, …).
        period_labels:  Year/quarter strings for each value column.
    """
    _draw_section_header(pdf, title)

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

    n = min(len(period_labels), 3)  # cap at 3 periods
    page_w = 190.0  # usable width (A4 − margins)
    label_w = 72.0
    val_w = (page_w - label_w) / n

    # ── Header row ────────────────────────────────────────────────────────────
    pdf.set_fill_color(_HDR_R, _HDR_G, _HDR_B)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(label_w, 7, text="  Metric", border=1, fill=True)
    for lbl in period_labels[:n]:
        pdf.cell(val_w, 7, text=lbl, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    # ── Data rows ─────────────────────────────────────────────────────────────
    for idx, row in enumerate(rows):
        label = _sanitize(str(row[0]))
        values = [str(v) for v in row[1 : n + 1]]

        # Determine row fill colour
        use_signed = label in _SIGNED_ROWS
        if use_signed and values:
            first_val = values[0]
            if first_val.startswith("-"):
                pdf.set_fill_color(_NEG_R, _NEG_G, _NEG_B)
            else:
                pdf.set_fill_color(_POS_R, _POS_G, _POS_B)
        elif idx % 2 == 0:
            pdf.set_fill_color(_ALT_R, _ALT_G, _ALT_B)
        else:
            pdf.set_fill_color(255, 255, 255)

        pdf.set_font("Arial", "B", 9)
        pdf.cell(label_w, 6, text=f"  {label}", border=1, fill=True)
        pdf.set_font("Arial", "", 9)
        for val in values:
            # Colour negative numbers in red text
            if val.startswith("-"):
                pdf.set_text_color(180, 40, 40)
            else:
                pdf.set_text_color(0, 0, 0)
            pdf.cell(val_w, 6, text=val, border=1, fill=True, align="R")
        pdf.set_text_color(0, 0, 0)
        pdf.ln()

    pdf.ln(4)


# ─────────────────────────────────────────────────────────────────────────────
# PDF helpers — backtest results
# ─────────────────────────────────────────────────────────────────────────────


def _draw_backtest_section(pdf: FPDF, bt: dict) -> None:
    """
    Render the backtest summary KPI grid and trade log table.
    """
    _draw_section_header(pdf, "Backtest Results")

    if not bt:
        pdf.set_font("Arial", "I", 9)
        pdf.cell(
            0,
            6,
            text="  Backtest unavailable (signals indicator must be active).",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(3)
        return

    # ── KPI summary grid ──────────────────────────────────────────────────────
    def _kpi_row(pairs: list[tuple[str, str, bool]]) -> None:
        """Render a row of KPI cells. Each tuple: (label, value, is_positive)."""
        cell_w = 190.0 / len(pairs)
        for lbl, val, positive in pairs:
            pdf.set_fill_color(40, 55, 90)
            pdf.set_text_color(180, 200, 230)
            pdf.set_font("Arial", "B", 7)
            pdf.cell(cell_w, 5, text=lbl.upper(), border=0, fill=True, align="C")
        pdf.ln()
        for lbl, val, positive in pairs:
            pdf.set_fill_color(50, 65, 105)
            if positive is True:
                pdf.set_text_color(100, 220, 140)
            elif positive is False:
                pdf.set_text_color(240, 100, 100)
            else:
                pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", "B", 11)
            pdf.cell(cell_w, 9, text=val, border=0, fill=True, align="C")
        pdf.ln()
        pdf.set_text_color(0, 0, 0)

    total_ret = bt.get("total_return_pct", 0.0)
    bh_ret = bt.get("buy_hold_return_pct", 0.0)
    alpha = bt.get("alpha_pct", 0.0)
    drawdown = bt.get("max_drawdown_pct", 0.0)
    sharpe = bt.get("sharpe_ratio", 0.0)
    win_rate = bt.get("win_rate", 0.0)
    final_val = bt.get("final_value", 0.0)
    init_cap = bt.get("initial_capital", 10000.0)

    _kpi_row(
        [
            ("Strategy Return", f"{total_ret:+.2f}%", total_ret >= 0),
            ("Buy & Hold", f"{bh_ret:+.2f}%", bh_ret >= 0),
            ("Alpha", f"{alpha:+.2f}%", alpha >= 0),
            ("Max Drawdown", f"{drawdown:.2f}%", drawdown >= -5),
        ]
    )
    pdf.ln(1)
    _kpi_row(
        [
            ("Initial Capital", f"${init_cap:,.0f}", None),
            ("Final Value", f"${final_val:,.2f}", final_val >= init_cap),
            ("Sharpe Ratio", f"{sharpe:.2f}", sharpe >= 1),
            ("Win Rate", f"{win_rate:.1f}%", win_rate >= 50),
        ]
    )
    pdf.ln(4)

    # ── Trade log ─────────────────────────────────────────────────────────────
    trades = bt.get("trades", [])
    if not trades:
        pdf.set_font("Arial", "I", 9)
        pdf.cell(0, 6, text="  No trades were executed.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        return

    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(
        0, 7, text=f"Trade Log  ({len(trades)} entries)", new_x="LMARGIN", new_y="NEXT"
    )

    col_widths = [
        18,
        20,
        22,
        26,
        26,
        26,
        26,
        26,
    ]  # Type Date Price Shares Value P&L P&L%
    headers = ["Type", "Date", "Price", "Shares", "Value", "P&L", "P&L %", ""]

    # Header
    pdf.set_fill_color(_HDR_R, _HDR_G, _HDR_B)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 8)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 6, text=h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0, 0, 0)

    # Rows
    for i, t in enumerate(trades):
        is_buy = t.kind == "BUY"
        pnl = t.pnl
        pnl_pct = t.pnl_pct

        fill = i % 2 == 0
        pdf.set_fill_color(245, 247, 252 if fill else 255)

        # Type cell coloured
        if is_buy:
            pdf.set_fill_color(225, 245, 230)
            pdf.set_text_color(30, 140, 60)
        else:
            (
                pdf.set_fill_color(250, 230, 230)
                if (pnl or 0) < 0
                else pdf.set_fill_color(225, 245, 230)
            )
            (
                pdf.set_text_color(180, 40, 40)
                if (pnl or 0) < 0
                else pdf.set_text_color(30, 140, 60)
            )

        pdf.set_font("Arial", "B", 8)
        pdf.cell(col_widths[0], 5, text=t.kind, border=1, fill=True, align="C")
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(245, 247, 252) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Arial", "", 8)

        date_str = (
            t.date.strftime("%Y-%m-%d")
            if hasattr(t.date, "strftime")
            else str(t.date)[:10]
        )
        row_vals = [
            date_str,
            f"${t.price:.2f}",
            f"{t.shares:.3f}",
            f"${t.value:,.2f}",
            f"${pnl:,.2f}" if pnl is not None else "-",
            f"{pnl_pct:+.2f}%" if pnl_pct is not None else "-",
            "",
        ]
        for w, v in zip(col_widths[1:], row_vals):
            pdf.cell(w, 5, text=v, border=1, fill=fill, align="R")
        pdf.ln()

    pdf.ln(4)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────


def generate_pdf_report(
    tickers: list,
    analyzed_data: dict,
    plots: dict,
    indicators: list | None = None,
    fundamentals_data: dict | None = None,
    comparison_plot: str | None = None,
    financial_statements: dict | None = None,
    backtest_results: dict | None = None,
    output_dir: str = "data",
) -> str:
    """
    Generate a comprehensive PDF report with:
      - Per-ticker key statistics table
      - Fundamental data table (when available)
      - Income Statement / P&L (when available)
      - Balance Sheet (when available)
      - Cash Flow Statement (when available)
      - Plain-English technical commentary
      - Backtest results + trade log (when available)
      - Technical analysis chart
      - Multi-ticker comparison chart (when provided)
    """
    if indicators is None:
        indicators = []
    if fundamentals_data is None:
        fundamentals_data = {}
    if financial_statements is None:
        financial_statements = {}
    if backtest_results is None:
        backtest_results = {}

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Cover / header ────────────────────────────────────────────────────────
    pdf.set_font("Arial", "B", 20)
    pdf.cell(
        0, 14, text="Stock Analysis Report", new_x="LMARGIN", new_y="NEXT", align="C"
    )

    pdf.set_font("Arial", "", 10)
    pdf.cell(
        0,
        7,
        text=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.cell(
        0,
        7,
        text=f"Tickers: {', '.join(tickers)}",
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )

    if indicators:
        label_str = ", ".join(_INDICATOR_LABELS.get(i) or i for i in indicators)
        pdf.set_font("Arial", "I", 9)
        pdf.multi_cell(0, 6, text=_sanitize(f"Indicators: {label_str}"), align="C")

    # Feature badges
    badges = []
    if financial_statements:
        badges.append("Financial Statements")
    if backtest_results:
        badges.append("Backtest")
    if badges:
        pdf.set_font("Arial", "I", 9)
        pdf.set_x(pdf.l_margin)  # ← FIX
        pdf.multi_cell(0, 5, text=f"Includes: {', '.join(badges)}", align="C")

    pdf.ln(6)

    # ── Comparison chart (multi-ticker) ───────────────────────────────────────
    if comparison_plot and os.path.exists(comparison_plot):
        pdf.set_font("Arial", "B", 13)
        pdf.cell(
            0, 9, text="Relative Performance Comparison", new_x="LMARGIN", new_y="NEXT"
        )
        pdf.image(comparison_plot, x=10, w=185)
        pdf.ln(6)

    # ── Per-ticker sections ───────────────────────────────────────────────────
    for ticker in tickers:
        data = analyzed_data.get(ticker)
        if data is None:
            continue

        pdf.add_page()

        # ── Ticker banner ─────────────────────────────────────────────────────
        pdf.set_fill_color(22, 33, 60)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 15)
        pdf.cell(0, 12, text=f"  {ticker}", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

        # ── Key Statistics ────────────────────────────────────────────────────
        _draw_section_header(pdf, "Key Statistics")
        summary_rows = _build_summary_rows(data, indicators)
        if summary_rows:
            _draw_two_col_table(pdf, summary_rows)
        pdf.ln(4)

        # ── Fundamental Data ──────────────────────────────────────────────────
        fund = fundamentals_data.get(ticker, {})
        if fund:
            _draw_section_header(pdf, "Fundamental Data")
            _draw_two_col_table(pdf, _build_fundamentals_rows(fund))
            pdf.ln(4)

        # ── Income Statement (P&L) ────────────────────────────────────────────
        stmts = financial_statements.get(ticker, {})
        if stmts:
            income = stmts.get("income_stmt")
            if income:
                rows, labels = income
                _draw_financial_table(pdf, "Income Statement (P&L)", rows, labels)

            # ── Balance Sheet ─────────────────────────────────────────────────
            balance = stmts.get("balance_sheet")
            if balance:
                rows, labels = balance
                _draw_financial_table(pdf, "Balance Sheet", rows, labels)

            # ── Cash Flow ─────────────────────────────────────────────────────
            cashflow = stmts.get("cashflow")
            if cashflow:
                rows, labels = cashflow
                _draw_financial_table(pdf, "Cash Flow Statement", rows, labels)

        # ── Technical Commentary ──────────────────────────────────────────────
        _draw_section_header(pdf, "Technical Commentary")
        pdf.set_font("Arial", "", 10)
        commentary = generate_trend_commentary(ticker, data, indicators)
        pdf.multi_cell(0, 6, text=_sanitize(commentary))
        pdf.ln(4)

        # ── Backtest Results ──────────────────────────────────────────────────
        bt = backtest_results.get(ticker)
        if bt is not None:
            _draw_backtest_section(pdf, bt)

        # ── Technical Chart ───────────────────────────────────────────────────
        plot_path = plots.get(ticker)
        if plot_path and os.path.exists(plot_path):
            _draw_section_header(pdf, "Technical Chart")
            pdf.image(plot_path, x=10, w=185)
            pdf.ln(4)

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, "stock_analysis_report.pdf")
    pdf.output(pdf_path)
    log.info(f"PDF report saved to {pdf_path}")
    return pdf_path
