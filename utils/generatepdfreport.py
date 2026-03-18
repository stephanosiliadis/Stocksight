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
# PDF helpers
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
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────


def generate_pdf_report(
    tickers: list,
    analyzed_data: dict,
    plots: dict,
    indicators: list | None = None,
    fundamentals_data: dict | None = None,
    comparison_plot: str | None = None,
    output_dir: str = "data",
) -> str:
    """
    Generate a comprehensive PDF report with:
      - Per-ticker key statistics table
      - Fundamental data table (when available)
      - Plain-English technical commentary
      - Technical analysis chart
      - Multi-ticker comparison chart (when provided)
    """
    if indicators is None:
        indicators = []
    if fundamentals_data is None:
        fundamentals_data = {}

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

        # Section header bar
        pdf.set_fill_color(40, 40, 60)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 15)
        pdf.cell(0, 11, text=f"  {ticker}", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

        # Key statistics table
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, text="Key Statistics", new_x="LMARGIN", new_y="NEXT")
        summary_rows = _build_summary_rows(data, indicators)
        if summary_rows:
            _draw_two_col_table(pdf, summary_rows)
        pdf.ln(4)

        # Fundamental data table
        fund = fundamentals_data.get(ticker, {})
        if fund:
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, text="Fundamental Data", new_x="LMARGIN", new_y="NEXT")
            _draw_two_col_table(pdf, _build_fundamentals_rows(fund))
            pdf.ln(4)

        # Technical commentary
        pdf.set_font("Arial", "B", 11)
        pdf.cell(0, 8, text="Technical Commentary", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Arial", "", 10)
        commentary = generate_trend_commentary(ticker, data, indicators)
        pdf.multi_cell(0, 6, text=_sanitize(commentary))
        pdf.ln(4)

        # Chart
        plot_path = plots.get(ticker)
        if plot_path and os.path.exists(plot_path):
            pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 8, text="Technical Chart", new_x="LMARGIN", new_y="NEXT")
            pdf.image(plot_path, x=10, w=185)
            pdf.ln(4)

    # ── Save ──────────────────────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, "stock_analysis_report.pdf")
    pdf.output(pdf_path)
    log.info(f"PDF report saved to {pdf_path}")
    return pdf_path
