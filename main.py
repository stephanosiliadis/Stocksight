"""
stocktool — CLI stock analysis tool
====================================

Usage examples
--------------
# Analyse Apple for the last year (all indicators):
    python main.py analyze -t AAPL

# Analyse multiple tickers over a specific period:
    python main.py analyze -t AAPL,TSLA,NVDA --period 6m

# Select only specific indicators:
    python main.py analyze -t AAPL -i rsi -i macd -i ema50 -i ema200

# Include fundamentals and a comparison chart:
    python main.py analyze -t AAPL,MSFT,GOOG --compare --fundamentals

# Include full financial statements (P&L, Balance Sheet, Cash Flow):
    python main.py analyze -t AAPL --statements

# Run a backtest using detected signals:
    python main.py analyze -t AAPL -i rsi -i macd -i signals --backtest

# Full analysis — everything enabled:
    python main.py analyze -t AAPL,MSFT --compare --fundamentals --statements --backtest

# Use explicit date range, skip Excel output:
    python main.py analyze -t TSLA --start 2024-01-01 --end 2024-12-31 --no-excel

# List all available indicators:
    python main.py list-indicators
"""

import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
import yaml
from dateutil.relativedelta import relativedelta
from rich.console import Console
from rich.table import Table

from utils.analyzedata import analyze_data, ALL_INDICATORS
from utils.cleandata import clean_data  # noqa: imported to satisfy package init
from utils.fetchstockdata import fetch_stock_data
from utils.generatepdfreport import generate_pdf_report
from utils.generateplots import generate_plots
from utils.savetoexcel import save_to_excel
from utils.stats import compute_range_stats

console = Console()

# ─── Typer app ────────────────────────────────────────────────────────────────
app = typer.Typer(
    name="stocktool",
    help="A CLI tool for comprehensive technical stock analysis.",
    add_completion=False,
)

# Preset period -> months
_PERIOD_MAP: dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "6m": 6,
    "1y": 12,
    "5y": 60,
}

DATA_DIR = "data"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _load_config() -> dict:
    for path in (Path("config.yaml"), Path("config.yml")):
        if path.exists():
            with open(path) as f:
                return yaml.safe_load(f) or {}
    return {}


def _resolve_dates(
    start: Optional[str],
    end: Optional[str],
    period: Optional[str],
) -> tuple[str, str]:
    """Compute concrete start/end date strings from the user's inputs."""
    end_date = end or datetime.today().strftime("%Y-%m-%d")

    if start:
        start_date = start
    elif period and period in _PERIOD_MAP:
        months = _PERIOD_MAP[period]
        start_date = (
            datetime.strptime(end_date, "%Y-%m-%d") - relativedelta(months=months)
        ).strftime("%Y-%m-%d")
    else:
        # Default to 1 year
        start_date = (
            datetime.strptime(end_date, "%Y-%m-%d") - relativedelta(months=12)
        ).strftime("%Y-%m-%d")

    return start_date, end_date


def _setup_logging(verbose: bool, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(output_dir, "stocktool.log")),
        ],
    )


# ─── Commands ─────────────────────────────────────────────────────────────────


@app.command()
def analyze(
    tickers: str = typer.Option(
        ...,
        "--tickers",
        "-t",
        help="Comma-separated ticker symbols, e.g. AAPL,TSLA,NVDA",
    ),
    start: Optional[str] = typer.Option(
        None,
        "--start",
        "-sd",
        help="Start date in YYYY-MM-DD format.",
    ),
    end: Optional[str] = typer.Option(
        None,
        "--end",
        "-ed",
        help="End date in YYYY-MM-DD format (default: today).",
    ),
    period: Optional[str] = typer.Option(
        None,
        "--period",
        "-p",
        help="Preset date range: 1m, 3m, 6m, 1y, 5y. Ignored when --start is set.",
    ),
    indicators: Optional[list[str]] = typer.Option(
        None,
        "--indicator",
        "-i",
        help=(
            "Indicator to include. Repeat the flag for multiple, e.g. -i rsi -i macd. "
            f"Options: {', '.join(ALL_INDICATORS)}. Default: all."
        ),
    ),
    no_pdf: bool = typer.Option(False, "--no-pdf", help="Skip PDF report generation."),
    no_excel: bool = typer.Option(False, "--no-excel", help="Skip Excel export."),
    compare: bool = typer.Option(
        False,
        "--compare",
        "-c",
        help="Generate a normalized multi-ticker price comparison chart.",
    ),
    fundamentals: bool = typer.Option(
        False,
        "--fundamentals",
        "-f",
        help="Fetch and include fundamental data (P/E, market cap, etc.) in the report.",
    ),
    statements: bool = typer.Option(
        False,
        "--statements",
        "-s",
        help=(
            "Fetch and include full financial statements "
            "(Income Statement / P&L, Balance Sheet, Cash Flow) in the report."
        ),
    ),
    backtest: bool = typer.Option(
        False,
        "--backtest",
        "-b",
        help=(
            "Run a signal-driven backtest and include results in the report. "
            "Requires the 'signals' indicator to be active."
        ),
    ),
    backtest_capital: float = typer.Option(
        10_000.0,
        "--capital",
        help="Starting capital for the backtest (default: $10,000).",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable debug logging."
    ),
):
    """
    Fetch, analyse, and report on one or more stock tickers.
    """
    config = _load_config()
    defaults = config.get("defaults", {})

    _setup_logging(verbose, DATA_DIR)
    log = logging.getLogger(__name__)

    os.makedirs(DATA_DIR, exist_ok=True)

    # ── Resolve indicators ────────────────────────────────────────────────────
    if not indicators:
        active_indicators = defaults.get("indicators", ALL_INDICATORS)
    else:
        active_indicators = [i.lower().strip() for i in indicators]
        unknown = [i for i in active_indicators if i not in ALL_INDICATORS]
        if unknown:
            console.print(
                f"[bold red]Unknown indicators: {', '.join(unknown)}[/bold red]\n"
                f"Valid options: {', '.join(ALL_INDICATORS)}"
            )
            raise typer.Exit(1)

    # Backtest requires signals; add it silently if missing
    if backtest and "signals" not in active_indicators:
        console.print(
            "[yellow]  ⚠  Backtest enabled but 'signals' indicator is not active — "
            "adding it automatically.[/yellow]"
        )
        active_indicators = list(active_indicators) + ["signals"]

    # ── Resolve tickers ───────────────────────────────────────────────────────
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    # ── Resolve dates ─────────────────────────────────────────────────────────
    effective_period = period or defaults.get("period", "1y")
    start_date, end_date = _resolve_dates(start, end, effective_period)

    # EMA200 needs ~200 trading days (~10 months) to fully populate.
    # Use 12 months of warmup to guarantee all indicators are fully seeded
    # regardless of the user's requested start date.
    warmup_start = (
        datetime.strptime(start_date, "%Y-%m-%d") - relativedelta(months=12)
    ).strftime("%Y-%m-%d")

    # ── Summary banner ────────────────────────────────────────────────────────
    console.rule("[bold cyan]Stock Analysis Tool[/bold cyan]")
    console.print(f"  Tickers   : [bold]{', '.join(ticker_list)}[/bold]")
    console.print(f"  Date range: {start_date} -> {end_date}")
    console.print(f"  Indicators: {', '.join(active_indicators)}")
    extras = []
    if fundamentals:
        extras.append("Fundamentals")
    if statements:
        extras.append("Financial Statements (P&L / Balance Sheet / Cash Flow)")
    if backtest:
        extras.append(f"Backtest (capital: ${backtest_capital:,.0f})")
    if extras:
        console.print(f"  Extras    : {', '.join(extras)}")
    console.print()

    # ── Per-ticker processing ─────────────────────────────────────────────────
    analyzed_data: dict = {}
    plots: dict = {}
    fundamentals_data: dict = {}
    financial_statements_data: dict = {}
    backtest_results: dict = {}
    range_stats: dict = {}

    for ticker in ticker_list:
        with console.status(f"[cyan]Processing {ticker}…[/cyan]"):
            stock_data = fetch_stock_data(ticker, warmup_start, end_date)
            if stock_data is None or stock_data.empty:
                console.print(f"  [yellow]⚠  No data for {ticker}, skipping.[/yellow]")
                continue

            full_analysis = analyze_data(stock_data, active_indicators)
            if full_analysis is None:
                console.print(
                    f"  [yellow]⚠  Analysis failed for {ticker}, skipping.[/yellow]"
                )
                continue

            # Trim warmup rows
            trimmed = full_analysis[full_analysis.index >= start_date].copy()
            analyzed_data[ticker] = trimmed

            # Historical high/low range stats for the selected date range
            range_stats[ticker] = compute_range_stats(trimmed)

            # Signals
            signals_data = None
            support_lvls = None
            resistance_lvls = None

            if "signals" in active_indicators:
                from utils.signals import detect_signals

                signals_data = detect_signals(trimmed, active_indicators)

            if "support_resistance" in active_indicators:
                from utils.signals import detect_support_resistance

                support_lvls, resistance_lvls = detect_support_resistance(trimmed)

            # Fundamentals
            if fundamentals:
                from utils.fundamentals import fetch_fundamentals

                fundamentals_data[ticker] = fetch_fundamentals(ticker)

            # Financial Statements (P&L, Balance Sheet, Cash Flow)
            if statements:
                from utils.financials import fetch_financial_statements

                stmts = fetch_financial_statements(ticker)
                if stmts:
                    financial_statements_data[ticker] = stmts
                    found = [
                        k
                        for k in ("income_stmt", "balance_sheet", "cashflow")
                        if k in stmts
                    ]
                    log.debug(f"[{ticker}] Statements fetched: {found}")
                else:
                    console.print(
                        f"  [yellow]⚠  No financial statements available for {ticker}.[/yellow]"
                    )

            # Backtest
            if backtest and signals_data is not None:
                from utils.backtest import run_backtest

                bt = run_backtest(
                    trimmed, signals_data, initial_capital=backtest_capital
                )
                backtest_results[ticker] = bt
                if bt:
                    ret = bt.get("total_return_pct", 0.0)
                    bh = bt.get("buy_hold_return_pct", 0.0)
                    console.print(
                        f"  [dim]Backtest [{ticker}]: "
                        f"strategy {ret:+.1f}%  |  B&H {bh:+.1f}%[/dim]"
                    )

            # Chart
            plots[ticker] = generate_plots(
                trimmed,
                ticker,
                active_indicators,
                signals_data=signals_data,
                support_levels=support_lvls,
                resistance_levels=resistance_lvls,
                output_dir=DATA_DIR,
            )

            rs = range_stats.get(ticker)
            if rs:
                hd = rs.get("period_high_date")
                ld = rs.get("period_low_date")
                hd_str = hd.strftime("%Y-%m-%d") if hasattr(hd, "strftime") else str(hd)
                ld_str = ld.strftime("%Y-%m-%d") if hasattr(ld, "strftime") else str(ld)
                console.print(
                    f"  [dim]Range [{ticker}]: "
                    f"High ${rs['period_high']:.2f} ({hd_str})  |  "
                    f"Low ${rs['period_low']:.2f} ({ld_str})[/dim]"
                )

        console.print(f"  [green]✓[/green] {ticker} done")

    if not analyzed_data:
        console.print("[bold red]No valid data fetched. Exiting.[/bold red]")
        raise typer.Exit(1)

    # ── Comparison chart ──────────────────────────────────────────────────────
    comparison_path = None
    if compare and len(analyzed_data) > 1:
        from utils.comparison import generate_comparison_plot

        comparison_path = generate_comparison_plot(analyzed_data, ticker_list, DATA_DIR)
        console.print(f"  [green]✓[/green] Comparison chart saved")

    # ── Excel export ──────────────────────────────────────────────────────────
    if not no_excel:
        excel_path = os.path.join(DATA_DIR, "stock_data.xlsx")
        save_to_excel(analyzed_data, excel_path, range_stats=range_stats)
        console.print(f"  [green]✓[/green] Excel saved -> {excel_path}")

    # ── PDF report ────────────────────────────────────────────────────────────
    if not no_pdf:
        pdf_path = generate_pdf_report(
            ticker_list,
            analyzed_data,
            plots,
            indicators=active_indicators,
            fundamentals_data=fundamentals_data,
            comparison_plot=comparison_path,
            financial_statements=financial_statements_data,
            backtest_results=backtest_results,
            range_stats=range_stats,
            output_dir=DATA_DIR,
        )
        console.print(f"  [green]✓[/green] PDF saved -> {pdf_path}")

    console.rule()
    console.print(
        f"[bold green]✓ Analysis complete for {', '.join(analyzed_data.keys())}[/bold green]"
    )


@app.command(name="list-indicators")
def list_indicators():
    """List all available technical indicators with descriptions."""
    descriptions = {
        "bollinger": (
            "Bollinger Bands",
            "Volatility bands around a moving average (upper/lower)",
        ),
        "rsi": ("RSI (14)", "Momentum oscillator 0–100; >70 overbought, <30 oversold"),
        "macd": ("MACD", "Trend-following momentum: MACD line, signal, histogram"),
        "ema20": ("EMA 20", "20-period Exponential Moving Average — short-term trend"),
        "ema50": ("EMA 50", "50-period EMA — medium-term trend"),
        "ema200": ("EMA 200", "200-period EMA — long-term trend benchmark"),
        "volume": ("Volume", "Bar chart coloured green/red by price direction"),
        "atr": ("ATR (14)", "Average True Range — daily volatility in price units"),
        "stochastic": (
            "Stochastic Oscillator",
            "Momentum: %K and %D lines; >80 overbought, <20 oversold",
        ),
        "signals": (
            "Buy / Sell Signals",
            "Markers from RSI crosses, MACD crossovers, EMA cross",
        ),
        "support_resistance": (
            "Support & Resistance",
            "Auto-detected key price levels from rolling extrema",
        ),
    }

    table = Table(title="Available Indicators", show_lines=True)
    table.add_column("Key", style="cyan bold", no_wrap=True)
    table.add_column("Name", style="white bold")
    table.add_column("Description", style="dim")

    for key, (name, desc) in descriptions.items():
        table.add_row(key, name, desc)

    console.print(table)
    console.print(
        "\n[dim]Usage: python main.py analyze -t AAPL -i rsi -i macd -i ema50[/dim]\n"
    )


# ─── Interactive wizard ───────────────────────────────────────────────────────
# Every prompt accepts 'b'/'back' to revisit the previous step and
# 'c'/'cancel'/'q' to abort the wizard entirely.

_TICKER_RE = re.compile(r"^[A-Za-z]+(\.[A-Za-z]+)?$")

_STEP_ORDER = [
    "tickers",
    "date_mode",
    "period",
    "start",
    "end",
    "indicator_mode",
    "indicators",
    "compare",
    "fundamentals",
    "statements",
    "backtest",
    "capital",
    "pdf",
    "excel",
    "verbose",
    "confirm",
]


def _read_raw(prompt: str) -> tuple[Optional[str], str]:
    hint = " [dim](Enter=default, b=back, c=cancel)[/dim]"
    raw = console.input(f"{prompt}{hint}: ").strip()
    low = raw.lower()
    if low in ("b", "back"):
        return None, "BACK"
    if low in ("c", "cancel", "q", "quit"):
        return None, "CANCEL"
    return raw, "OK"


def _ask_yes_no(prompt: str, default: bool = True):
    marker = "Y/n" if default else "y/N"
    while True:
        raw, sig = _read_raw(f"{prompt} [{marker}]")
        if sig != "OK":
            return None, sig
        if raw == "":
            return default, "OK"
        if raw is not None:
            if raw.lower() in ("y", "yes"):
                return True, "OK"
            if raw.lower() in ("n", "no"):
                return False, "OK"
        console.print("[red]  Please answer y or n.[/red]")


def _ask_choice(prompt: str, choices: list[str], default: Optional[str] = None):
    choice_str = "/".join(choices)
    while True:
        raw, sig = _read_raw(
            f"{prompt} ({choice_str})" + (f" [{default}]" if default else "")
        )
        if sig != "OK":
            return None, sig
        if raw == "" and default:
            return default, "OK"
        if raw is not None:
            if raw.lower() in choices:
                return raw.lower(), "OK"
        console.print(f"[red]  Please choose one of: {choice_str}[/red]")


def _ask_date(prompt: str, default: Optional[str] = None):
    while True:
        raw, sig = _read_raw(
            f"{prompt} (YYYY-MM-DD)" + (f" [{default}]" if default else "")
        )
        if sig != "OK":
            return None, sig
        if raw == "" and default:
            return default, "OK"
        if raw == "" and not default:
            return "", "OK"
        if raw is None:
            return None, "OK"
        try:
            d = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            console.print("[red]  Invalid date — use YYYY-MM-DD.[/red]")
            continue
        if d > datetime.today():
            console.print("[red]  Date cannot be in the future.[/red]")
            continue
        return raw, "OK"


def _ask_float(prompt: str, default: Optional[float] = None, minimum: float = 0.0):
    while True:
        raw, sig = _read_raw(
            f"{prompt}" + (f" [{default}]" if default is not None else "")
        )
        if sig != "OK":
            return None, sig
        if raw == "" and default is not None:
            return float(default), "OK"
        if raw is None:
            return None, "OK"
        try:
            v = float(raw)
        except ValueError:
            console.print("[red]  Please enter a number.[/red]")
            continue
        if v <= minimum:
            console.print(f"[red]  Value must be greater than {minimum}.[/red]")
            continue
        return v, "OK"


def _ask_tickers(default: Optional[str] = None):
    while True:
        raw, sig = _read_raw(
            "Ticker symbols (comma-separated, e.g. AAPL,TSLA,NVDA)"
            + (f" [{default}]" if default else "")
        )
        if sig != "OK":
            return None, sig
        if raw == "" and default:
            raw = default
        if raw is not None:
            parts = [t.strip().upper() for t in raw.split(",") if t.strip()]
            if not parts:
                console.print("[red]  At least one ticker is required.[/red]")
                continue
            bad = [t for t in parts if not _TICKER_RE.match(t)]
            if bad:
                console.print(f"[red]  Invalid ticker format: {', '.join(bad)}[/red]")
                continue
            return ",".join(parts), "OK"


def _ask_indicators(default_list: list[str]):
    default_str = ",".join(default_list)
    while True:
        raw, sig = _read_raw(
            f"Indicators (comma-separated: {', '.join(ALL_INDICATORS)}) [{default_str}]"
        )
        if sig != "OK":
            return None, sig
        if raw == "":
            raw = default_str
        if raw is not None:
            parts = [i.strip().lower() for i in raw.split(",") if i.strip()]
            unknown = [i for i in parts if i not in ALL_INDICATORS]
            if not parts:
                console.print("[red]  At least one indicator must be selected.[/red]")
                continue
            if unknown:
                console.print(f"[red]  Unknown indicators: {', '.join(unknown)}[/red]")
                continue
            return parts, "OK"


def _step_applicable(step_id: str, answers: dict) -> bool:
    if step_id == "period":
        return answers.get("date_mode") == "preset"
    if step_id in ("start", "end"):
        return answers.get("date_mode") == "custom"
    if step_id == "indicators":
        return answers.get("indicator_mode") == "select"
    if step_id == "compare":
        tickers = answers.get("tickers", "")
        return len([t for t in tickers.split(",") if t.strip()]) > 1
    if step_id == "capital":
        return answers.get("backtest") is True
    return True


def _print_summary(answers: dict) -> None:
    table = Table(title="Configuration Summary", show_header=False)
    table.add_column("Field", style="cyan bold")
    table.add_column("Value", style="white")
    table.add_row("Tickers", answers.get("tickers", ""))
    if answers.get("date_mode") == "preset":
        table.add_row("Period", answers.get("period", ""))
    else:
        table.add_row("Start", answers.get("start", ""))
        table.add_row("End", answers.get("end") or "today")
    table.add_row(
        "Indicators",
        (
            "All"
            if answers.get("indicator_mode") == "all"
            else ", ".join(answers.get("indicators", []))
        ),
    )
    table.add_row("Compare", "Yes" if answers.get("compare") else "No")
    table.add_row("Fundamentals", "Yes" if answers.get("fundamentals") else "No")
    table.add_row("Statements", "Yes" if answers.get("statements") else "No")
    table.add_row(
        "Backtest",
        f"Yes (${answers['capital']:,.0f})" if answers.get("backtest") else "No",
    )
    table.add_row("PDF Report", "Yes" if answers.get("pdf") else "No")
    table.add_row("Excel Export", "Yes" if answers.get("excel") else "No")
    table.add_row("Verbose", "Yes" if answers.get("verbose") else "No")
    console.print()
    console.print(table)
    console.print()


def _run_step(step_id: str, answers: dict, defaults: dict):
    if step_id == "tickers":
        return _ask_tickers(default=answers.get("tickers"))
    if step_id == "date_mode":
        val, sig = _ask_yes_no("Use a preset period?", default=True)
        return (("preset" if val else "custom"), sig) if sig == "OK" else (val, sig)
    if step_id == "period":
        return _ask_choice(
            "Period",
            ["1m", "3m", "6m", "1y", "5y"],
            default=defaults.get("period", "1y"),
        )
    if step_id == "start":
        return _ask_date("Start date", default=answers.get("start"))
    if step_id == "end":
        return _ask_date("End date (blank = today)", default=answers.get("end") or "")
    if step_id == "indicator_mode":
        val, sig = _ask_yes_no("Use all indicators? (recommended)", default=True)
        return (("all" if val else "select"), sig) if sig == "OK" else (val, sig)
    if step_id == "indicators":
        return _ask_indicators(defaults.get("indicators", ALL_INDICATORS))
    if step_id == "compare":
        return _ask_yes_no("Generate comparison chart?", default=False)
    if step_id == "fundamentals":
        return _ask_yes_no(
            "Fetch fundamental data (P/E, market cap, ...)?", default=False
        )
    if step_id == "statements":
        return _ask_yes_no(
            "Fetch full financial statements (P&L, Balance Sheet, Cash Flow)?",
            default=False,
        )
    if step_id == "backtest":
        return _ask_yes_no("Run a signal-driven backtest?", default=False)
    if step_id == "capital":
        return _ask_float(
            "Starting capital for backtest", default=10_000.0, minimum=0.0
        )
    if step_id == "pdf":
        return _ask_yes_no("Generate PDF report?", default=True)
    if step_id == "excel":
        return _ask_yes_no("Generate Excel workbook?", default=True)
    if step_id == "verbose":
        return _ask_yes_no("Enable verbose / debug logging?", default=False)
    if step_id == "confirm":
        _print_summary(answers)
        val, sig = _ask_yes_no("Proceed with analysis?", default=True)
        if sig != "OK":
            return val, sig
        return (True, "OK") if val else (None, "BACK")
    raise ValueError(f"Unknown step: {step_id}")


def _build_kwargs(answers: dict, defaults: dict) -> dict:
    return dict(
        tickers=answers["tickers"],
        start=answers.get("start") or None,
        end=answers.get("end") or None,
        period=answers.get("period") if answers.get("date_mode") == "preset" else None,
        indicators=(
            None
            if answers.get("indicator_mode") == "all"
            else answers.get("indicators")
        ),
        no_pdf=not answers.get("pdf", True),
        no_excel=not answers.get("excel", True),
        compare=answers.get("compare", False),
        fundamentals=answers.get("fundamentals", False),
        statements=answers.get("statements", False),
        backtest=answers.get("backtest", False),
        backtest_capital=answers.get("capital", 10_000.0),
        verbose=answers.get("verbose", False),
    )


def run_interactive_wizard(defaults: dict) -> Optional[dict]:
    """Guided step-by-step menu with full back/cancel support at every prompt."""
    console.print()
    console.rule("[bold cyan]📊  Stock Analysis Tool — Interactive Mode[/bold cyan]")
    console.print(
        "[dim]Press Enter to accept defaults · type 'b' to go back · 'c' to cancel[/dim]\n"
    )

    answers: dict = {}
    idx = 0

    while 0 <= idx < len(_STEP_ORDER):
        step_id = _STEP_ORDER[idx]
        if not _step_applicable(step_id, answers):
            idx += 1
            continue

        result, sig = _run_step(step_id, answers, defaults)

        if sig == "CANCEL":
            console.print("\n[yellow]Cancelled — no analysis was run.[/yellow]")
            return None

        if sig == "BACK":
            idx -= 1
            while idx >= 0 and not _step_applicable(_STEP_ORDER[idx], answers):
                idx -= 1
            if idx < 0:
                console.print("\n[yellow]Cancelled — no analysis was run.[/yellow]")
                return None
            continue

        answers[step_id] = result
        idx += 1

    return _build_kwargs(answers, defaults)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No flags provided — launch the guided interactive menu.
        _cfg = _load_config()
        _kwargs = run_interactive_wizard(_cfg.get("defaults", {}))
        if _kwargs is not None:
            analyze(**_kwargs)
    else:
        app()
