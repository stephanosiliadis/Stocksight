import logging
import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)

# ── Key rows to extract from each statement ──────────────────────────────────

_INCOME_KEYS = [
    "Total Revenue",
    "Cost Of Revenue",
    "Gross Profit",
    "Operating Income",
    "Ebitda",
    "Pretax Income",
    "Tax Provision",
    "Net Income",
    "Basic EPS",
    "Diluted EPS",
]

_BALANCE_KEYS = [
    "Cash And Cash Equivalents",
    "Total Current Assets",
    "Total Assets",
    "Total Current Liabilities",
    "Total Liabilities Net Minority Interest",
    "Stockholders Equity",
    "Total Debt",
    "Long Term Debt",
    "Retained Earnings",
    "Working Capital",
]

_CASHFLOW_KEYS = [
    "Operating Cash Flow",
    "Capital Expenditure",
    "Free Cash Flow",
    "Investing Cash Flow",
    "Financing Cash Flow",
    "Issuance Of Debt",
    "Repayment Of Debt",
    "Repurchase Of Capital Stock",
    "Cash Dividends Paid",
    "Changes In Cash",
]

# Human-readable label overrides
_LABEL_MAP = {
    "Total Liabilities Net Minority Interest": "Total Liabilities",
    "Cash And Cash Equivalents": "Cash & Equivalents",
    "Issuance Of Debt": "Debt Issued",
    "Repayment Of Debt": "Debt Repaid",
    "Repurchase Of Capital Stock": "Share Buybacks",
    "Cash Dividends Paid": "Dividends Paid",
    "Ebitda": "EBITDA",
}


# ── Formatting helpers ────────────────────────────────────────────────────────


def _fmt_value(val) -> str:
    """Format a financial value into a human-readable string."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        v = float(val)
        sign = "-" if v < 0 else ""
        abs_v = abs(v)
        if abs_v >= 1e12:
            return f"{sign}${abs_v / 1e12:.2f}T"
        if abs_v >= 1e9:
            return f"{sign}${abs_v / 1e9:.2f}B"
        if abs_v >= 1e6:
            return f"{sign}${abs_v / 1e6:.2f}M"
        if abs_v >= 1e3:
            return f"{sign}${abs_v / 1e3:.2f}K"
        return f"{sign}${abs_v:.2f}"
    except (TypeError, ValueError):
        return str(val)


def _extract_rows(
    df: pd.DataFrame,
    keys: list[str],
    max_periods: int = 3,
) -> tuple[list[tuple], list[str]]:
    """
    Extract key rows from a financial DataFrame.

    Returns:
        rows          — list of (display_label, val_period0, val_period1, …)
        period_labels — list of year strings matching the value columns
    """
    if df is None or df.empty:
        return [], []

    # Most recent periods first; keep up to max_periods
    cols = df.columns[:max_periods]
    period_labels = []
    for c in cols:
        try:
            period_labels.append(pd.Timestamp(c).strftime("%Y"))
        except Exception:
            period_labels.append(str(c)[:4])

    rows: list[tuple] = []
    for key in keys:
        # Case-insensitive lookup
        match = next((k for k in df.index if k.lower() == key.lower()), None)
        if match is None:
            continue
        label = _LABEL_MAP.get(match, match)
        vals = tuple(_fmt_value(df.loc[match, c]) for c in cols)
        rows.append((label,) + vals)

    return rows, period_labels


# ── Public API ────────────────────────────────────────────────────────────────


def fetch_financial_statements(ticker: str, quarterly: bool = False) -> dict:
    """
    Fetch the three core financial statements from Yahoo Finance.

    Args:
        ticker:    Stock ticker symbol.
        quarterly: If True, fetch quarterly data instead of annual.

    Returns:
        Dict with keys ``'income_stmt'``, ``'balance_sheet'``, ``'cashflow'``.
        Each value is ``(rows, period_labels)`` ready for PDF rendering.
        Missing statements are omitted from the dict.
    """
    result: dict = {}
    try:
        t = yf.Ticker(ticker)

        pairs = [
            ("income_stmt", t.quarterly_income_stmt if quarterly else t.income_stmt, _INCOME_KEYS),
            ("balance_sheet", t.quarterly_balance_sheet if quarterly else t.balance_sheet, _BALANCE_KEYS),
            ("cashflow", t.quarterly_cashflow if quarterly else t.cashflow, _CASHFLOW_KEYS),
        ]

        for key, df, row_keys in pairs:
            try:
                if df is not None and not df.empty:
                    rows, labels = _extract_rows(df, row_keys)
                    if rows:
                        result[key] = (rows, labels)
            except Exception as e:
                log.warning(f"[{ticker}] Could not parse {key}: {e}")

    except Exception as e:
        log.warning(f"Could not fetch financial statements for {ticker}: {e}")

    return result
