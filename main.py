"""
stocktool — CLI stock analysis tool
====================================

Usage examples
--------------
# Interactive mode (no arguments — works when double-clicking an .exe too):
    python main.py

# Analyse Apple for the last year (all indicators):
    python main.py analyze -t AAPL

# Analyse multiple tickers over a specific period:
    python main.py analyze -t AAPL,TSLA,NVDA --period 6m

# Select only specific indicators:
    python main.py analyze -t AAPL -i rsi -i macd -i ema50 -i ema200

# Include fundamentals and a comparison chart:
    python main.py analyze -t AAPL,MSFT,GOOG --compare --fundamentals

# Use explicit date range, skip Excel output:
    python main.py analyze -t TSLA --start 2024-01-01 --end 2024-12-31 --no-excel

# List all available indicators:
    python main.py list-indicators
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
import yaml
from dateutil.relativedelta import relativedelta
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from utils.analyzedata import analyze_data, ALL_INDICATORS
from utils.cleandata import clean_data  # noqa: imported to satisfy package init
from utils.fetchstockdata import fetch_stock_data
from utils.generatepdfreport import generate_pdf_report
from utils.generateplots import generate_plots
from utils.savetoexcel import save_to_excel

console = Console()

# ─── Typer app ────────────────────────────────────────────────────────────────
app = typer.Typer(
    name="stocktool",
    help="A CLI tool for comprehensive technical stock analysis.",
    add_completion=False,
    invoke_without_command=True,  # lets the callback fire with no subcommand
)

# Preset period -> months
_PERIOD_MAP: dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "6m": 6,
    "1y": 12,
    "5y": 60,
}

# Human-readable names used in the interactive indicator table
_INDICATOR_NAMES: dict[str, str] = {
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

DATA_DIR = "data"
_DATE_FMT = "%Y-%m-%d"


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
    end_date = end or datetime.today().strftime(_DATE_FMT)

    if start:
        start_date = start
    elif period and period in _PERIOD_MAP:
        months = _PERIOD_MAP[period]
        start_date = (
            datetime.strptime(end_date, _DATE_FMT) - relativedelta(months=months)
        ).strftime(_DATE_FMT)
    else:
        start_date = (
            datetime.strptime(end_date, _DATE_FMT) - relativedelta(months=12)
        ).strftime(_DATE_FMT)

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


# ─── Validation ───────────────────────────────────────────────────────────────


def _parse_date(value: str) -> datetime:
    """Parse a YYYY-MM-DD string, raising ValueError with a clear message."""
    try:
        return datetime.strptime(value.strip(), _DATE_FMT)
    except ValueError:
        raise ValueError(f"'{value}' is not a valid date. Use YYYY-MM-DD format.")


def _validate_params(
    ticker_list: list[str],
    start: Optional[str],
    end: Optional[str],
    period: Optional[str],
    active_indicators: list[str],
) -> None:
    """
    Validate all resolved parameters and raise typer.BadParameter (or Exit)
    with a descriptive error message on any failure. Called from both the
    flag-driven path and after the interactive menu.
    """
    # Tickers
    if not ticker_list:
        console.print("[bold red]✗ No tickers provided.[/bold red]")
        raise typer.Exit(1)
    for t in ticker_list:
        if not t.isalpha() and "." not in t:
            console.print(
                f"[bold red]✗ Ticker '{t}' looks invalid "
                f"(expected letters, optionally with a '.' suffix like KARE.AT).[/bold red]"
            )
            raise typer.Exit(1)

    # Period
    if period is not None and period not in _PERIOD_MAP:
        console.print(
            f"[bold red]✗ Unknown period '{period}'. "
            f"Valid options: {', '.join(_PERIOD_MAP)}[/bold red]"
        )
        raise typer.Exit(1)

    # Dates (only when explicit dates are used, not period)
    today = datetime.today()
    if start:
        try:
            start_dt = _parse_date(start)
        except ValueError as e:
            console.print(f"[bold red]✗ Start date — {e}[/bold red]")
            raise typer.Exit(1)
        if start_dt > today:
            console.print("[bold red]✗ Start date cannot be in the future.[/bold red]")
            raise typer.Exit(1)
        if end:
            try:
                end_dt = _parse_date(end)
            except ValueError as e:
                console.print(f"[bold red]✗ End date — {e}[/bold red]")
                raise typer.Exit(1)
            if end_dt < start_dt:
                console.print(
                    f"[bold red]✗ End date ({end}) is before start date ({start}).[/bold red]"
                )
                raise typer.Exit(1)
            if end_dt > today:
                console.print(
                    "[bold red]✗ End date cannot be in the future.[/bold red]"
                )
                raise typer.Exit(1)

    # Indicators
    unknown = [i for i in active_indicators if i not in ALL_INDICATORS]
    if unknown:
        console.print(
            f"[bold red]✗ Unknown indicator(s): {', '.join(unknown)}\n"
            f"Valid options: {', '.join(ALL_INDICATORS)}[/bold red]"
        )
        raise typer.Exit(1)
    if not active_indicators:
        console.print("[bold red]✗ At least one indicator must be selected.[/bold red]")
        raise typer.Exit(1)


# ─── Interactive menu ─────────────────────────────────────────────────────────


def _interactive_menu(config_defaults: dict) -> dict:
    """
    Collect all analysis parameters interactively via the terminal.
    Returns a dict of resolved parameters ready for _run_analysis().
    """
    console.print(
        Panel.fit(
            Text("📊  Stock Analysis Tool", style="bold cyan", justify="center"),
            subtitle="[dim]Interactive Mode — press Ctrl+C to exit[/dim]",
        )
    )
    console.print()

    params: dict = {}

    # ── Tickers ──────────────────────────────────────────────────────────────
    while True:
        raw = Prompt.ask(
            "[bold]Ticker symbols[/bold] (comma-separated, e.g. [cyan]AAPL,TSLA,NVDA[/cyan])"
        )
        ticker_list = [t.strip().upper() for t in raw.split(",") if t.strip()]
        if not ticker_list:
            console.print("[red]  ✗ Enter at least one ticker.[/red]")
            continue
        bad = [t for t in ticker_list if not t.replace(".", "").isalpha()]
        if bad:
            console.print(
                f"[red]  ✗ These look invalid: {', '.join(bad)}. "
                "Use letters only (e.g. AAPL, KARE.AT).[/red]"
            )
            continue
        params["tickers"] = ticker_list
        break

    # ── Date range ────────────────────────────────────────────────────────────
    console.print()
    use_period = Confirm.ask("Use a [bold]preset period[/bold]?", default=True)

    if use_period:
        periods_str = ", ".join(f"[cyan]{p}[/cyan]" for p in _PERIOD_MAP)
        while True:
            period = Prompt.ask(
                f"Period ({periods_str})",
                default=config_defaults.get("period", "1y"),
            )
            if period in _PERIOD_MAP:
                params["period"] = period
                params["start"] = None
                params["end"] = None
                break
            console.print(
                f"[red]  ✗ Invalid period. Choose from: {', '.join(_PERIOD_MAP)}[/red]"
            )
    else:
        today_str = datetime.today().strftime(_DATE_FMT)

        while True:
            start_raw = Prompt.ask("Start date [bold](YYYY-MM-DD)[/bold]")
            try:
                start_dt = _parse_date(start_raw)
                if start_dt > datetime.today():
                    console.print("[red]  ✗ Start date cannot be in the future.[/red]")
                    continue
                params["start"] = start_dt.strftime(_DATE_FMT)
                break
            except ValueError as e:
                console.print(f"[red]  ✗ {e}[/red]")

        while True:
            end_raw = Prompt.ask(
                "End date [bold](YYYY-MM-DD)[/bold]", default=today_str
            )
            try:
                end_dt = _parse_date(end_raw)
                start_dt = _parse_date(params["start"])
                if end_dt < start_dt:
                    console.print(
                        f"[red]  ✗ End date ({end_raw}) is before "
                        f"start date ({params['start']}).[/red]"
                    )
                    continue
                if end_dt > datetime.today():
                    console.print("[red]  ✗ End date cannot be in the future.[/red]")
                    continue
                params["end"] = end_dt.strftime(_DATE_FMT)
                params["period"] = None
                break
            except ValueError as e:
                console.print(f"[red]  ✗ {e}[/red]")

    # ── Indicators ────────────────────────────────────────────────────────────
    console.print()
    use_all_ind = Confirm.ask(
        "Use [bold]all indicators[/bold]? (recommended)", default=True
    )

    if use_all_ind:
        params["indicators"] = list(ALL_INDICATORS)
    else:
        table = Table(show_lines=True, title="Available Indicators")
        table.add_column("#", style="cyan bold", width=3, justify="right")
        table.add_column("Key", style="bold")
        table.add_column("Name", style="white")
        for idx, key in enumerate(ALL_INDICATORS, 1):
            table.add_row(str(idx), key, _INDICATOR_NAMES.get(key, key))
        console.print(table)
        console.print(
            "[dim]Enter numbers (e.g. [cyan]1,3,5[/cyan]) or key names "
            "(e.g. [cyan]rsi,macd[/cyan]) — or mix both.[/dim]"
        )

        while True:
            raw_sel = Prompt.ask("Select indicators")
            selected: list[str] = []
            valid = True
            for item in raw_sel.split(","):
                item = item.strip()
                if not item:
                    continue
                if item.isdigit():
                    idx = int(item) - 1
                    if 0 <= idx < len(ALL_INDICATORS):
                        selected.append(ALL_INDICATORS[idx])
                    else:
                        console.print(
                            f"[red]  ✗ Number {item} is out of range "
                            f"(1–{len(ALL_INDICATORS)}).[/red]"
                        )
                        valid = False
                        break
                elif item.lower() in ALL_INDICATORS:
                    selected.append(item.lower())
                else:
                    console.print(
                        f"[red]  ✗ Unknown indicator '{item}'. "
                        f"Valid: {', '.join(ALL_INDICATORS)}[/red]"
                    )
                    valid = False
                    break
            if not valid:
                continue
            if not selected:
                console.print("[red]  ✗ Select at least one indicator.[/red]")
                continue
            # De-duplicate while preserving order
            seen: set[str] = set()
            params["indicators"] = [
                x for x in selected if not (x in seen or seen.add(x))  # type: ignore[func-returns-value]
            ]
            break

    # ── Options ───────────────────────────────────────────────────────────────
    console.print()

    if len(params["tickers"]) > 1:
        params["compare"] = Confirm.ask(
            "Generate normalised [bold]comparison chart[/bold]?", default=False
        )
    else:
        params["compare"] = False

    params["fundamentals"] = Confirm.ask(
        "Fetch [bold]fundamental data[/bold] (P/E, market cap, …)?", default=False
    )
    params["no_pdf"] = not Confirm.ask(
        "Generate [bold]PDF report[/bold]?", default=True
    )
    params["no_excel"] = not Confirm.ask(
        "Generate [bold]Excel workbook[/bold]?", default=True
    )
    params["verbose"] = Confirm.ask(
        "Enable [bold]verbose / debug logging[/bold]?", default=False
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    console.print()
    console.rule("[bold]Configuration Summary[/bold]")

    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column("Key", style="dim")
    summary.add_column("Value", style="bold")

    summary.add_row("Tickers", ", ".join(params["tickers"]))

    if params.get("period"):
        summary.add_row("Period", params["period"])
    else:
        summary.add_row("Start", params["start"])
        summary.add_row("End", params["end"])

    summary.add_row(
        "Indicators",
        (
            ", ".join(params["indicators"])
            if len(params["indicators"]) <= 6
            else f"{len(params['indicators'])} selected"
        ),
    )
    summary.add_row("Compare chart", "Yes" if params["compare"] else "No")
    summary.add_row("Fundamentals", "Yes" if params["fundamentals"] else "No")
    summary.add_row("PDF report", "No" if params["no_pdf"] else "Yes")
    summary.add_row("Excel export", "No" if params["no_excel"] else "Yes")

    console.print(summary)
    console.print()

    if not Confirm.ask("[bold]Proceed with analysis?[/bold]", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)

    console.print()
    return params


# ─── Shared analysis runner ───────────────────────────────────────────────────


def _run_analysis(
    ticker_list: list[str],
    active_indicators: list[str],
    start: Optional[str],
    end: Optional[str],
    period: Optional[str],
    compare: bool,
    fundamentals: bool,
    no_pdf: bool,
    no_excel: bool,
    verbose: bool,
) -> None:
    """Execute the full fetch -> analyse -> export pipeline."""
    _setup_logging(verbose, DATA_DIR)
    os.makedirs(DATA_DIR, exist_ok=True)

    start_date, end_date = _resolve_dates(start, end, period)

    warmup_start = (
        datetime.strptime(start_date, _DATE_FMT) - relativedelta(months=12)
    ).strftime(_DATE_FMT)

    console.rule("[bold cyan]Stock Analysis Tool[/bold cyan]")
    console.print(f"  Tickers   : [bold]{', '.join(ticker_list)}[/bold]")
    console.print(f"  Date range: {start_date} -> {end_date}")
    console.print(f"  Indicators: {', '.join(active_indicators)}")
    console.print()

    analyzed_data: dict = {}
    plots: dict = {}
    fundamentals_data: dict = {}

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

            trimmed = full_analysis[full_analysis.index >= start_date].copy()
            analyzed_data[ticker] = trimmed

            signals_data = None
            support_lvls = None
            resistance_lvls = None

            if "signals" in active_indicators:
                from utils.signals import detect_signals

                signals_data = detect_signals(trimmed, active_indicators)

            if "support_resistance" in active_indicators:
                from utils.signals import detect_support_resistance

                support_lvls, resistance_lvls = detect_support_resistance(trimmed)

            if fundamentals:
                from utils.fundamentals import fetch_fundamentals

                fundamentals_data[ticker] = fetch_fundamentals(ticker)

            plots[ticker] = generate_plots(
                trimmed,
                ticker,
                active_indicators,
                signals_data=signals_data,
                support_levels=support_lvls,
                resistance_levels=resistance_lvls,
                output_dir=DATA_DIR,
            )

        console.print(f"  [green]✓[/green] {ticker} done")

    if not analyzed_data:
        console.print("[bold red]No valid data fetched. Exiting.[/bold red]")
        raise typer.Exit(1)

    comparison_path = None
    if compare and len(analyzed_data) > 1:
        from utils.comparison import generate_comparison_plot

        comparison_path = generate_comparison_plot(analyzed_data, ticker_list, DATA_DIR)
        console.print("  [green]✓[/green] Comparison chart saved")

    if not no_excel:
        excel_path = os.path.join(DATA_DIR, "stock_data.xlsx")
        save_to_excel(analyzed_data, excel_path)
        console.print(f"  [green]✓[/green] Excel saved -> {excel_path}")

    if not no_pdf:
        pdf_path = generate_pdf_report(
            ticker_list,
            analyzed_data,
            plots,
            indicators=active_indicators,
            fundamentals_data=fundamentals_data,
            comparison_plot=comparison_path,
            output_dir=DATA_DIR,
        )
        console.print(f"  [green]✓[/green] PDF saved -> {pdf_path}")

    console.rule()
    console.print(
        f"[bold green]✓ Analysis complete for "
        f"{', '.join(analyzed_data.keys())}[/bold green]"
    )

    # When running as a bundled .exe, pause so the window doesn't vanish
    if getattr(sys, "frozen", False):
        console.print()
        input("Press Enter to exit…")


# ─── App callback — fires when no subcommand is given ─────────────────────────


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """
    When stocktool is launched without any subcommand (e.g. double-clicking
    the .exe, or running `python main.py` with no arguments), drop straight
    into the interactive menu.
    """
    if ctx.invoked_subcommand is None:
        config = _load_config()
        defaults = config.get("defaults", {})
        params = _interactive_menu(defaults)

        _validate_params(
            params["tickers"],
            params.get("start"),
            params.get("end"),
            params.get("period"),
            params["indicators"],
        )

        _run_analysis(
            ticker_list=params["tickers"],
            active_indicators=params["indicators"],
            start=params.get("start"),
            end=params.get("end"),
            period=params.get("period"),
            compare=params["compare"],
            fundamentals=params["fundamentals"],
            no_pdf=params["no_pdf"],
            no_excel=params["no_excel"],
            verbose=params["verbose"],
        )


# ─── Commands ─────────────────────────────────────────────────────────────────


@app.command()
def analyze(
    tickers: Optional[str] = typer.Option(
        None,
        "--tickers",
        "-t",
        help="Comma-separated ticker symbols, e.g. AAPL,TSLA,NVDA",
    ),
    start: Optional[str] = typer.Option(
        None,
        "--start",
        "-s",
        help="Start date in YYYY-MM-DD format.",
    ),
    end: Optional[str] = typer.Option(
        None,
        "--end",
        "-e",
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
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable debug logging."
    ),
):
    """
    Fetch, analyse, and report on one or more stock tickers.

    When called with no --tickers flag, the interactive menu is launched.
    """
    config = _load_config()
    defaults = config.get("defaults", {})

    # If tickers are missing, fall back to the interactive menu
    if tickers is None:
        params = _interactive_menu(defaults)

        _validate_params(
            params["tickers"],
            params.get("start"),
            params.get("end"),
            params.get("period"),
            params["indicators"],
        )

        _run_analysis(
            ticker_list=params["tickers"],
            active_indicators=params["indicators"],
            start=params.get("start"),
            end=params.get("end"),
            period=params.get("period"),
            compare=params["compare"],
            fundamentals=params["fundamentals"],
            no_pdf=params["no_pdf"],
            no_excel=params["no_excel"],
            verbose=params["verbose"],
        )
        return

    # ── Flag-driven path ──────────────────────────────────────────────────────
    if not indicators:
        active_indicators: list[str] = defaults.get("indicators", list(ALL_INDICATORS))
    else:
        active_indicators = [i.lower().strip() for i in indicators]

    effective_period = period or defaults.get("period", "1y")
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    # Validate everything before touching the network
    _validate_params(
        ticker_list,
        start,
        end,
        effective_period if not start else period,
        active_indicators,
    )

    _run_analysis(
        ticker_list=ticker_list,
        active_indicators=active_indicators,
        start=start,
        end=end,
        period=effective_period,
        compare=compare,
        fundamentals=fundamentals,
        no_pdf=no_pdf,
        no_excel=no_excel,
        verbose=verbose,
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


if __name__ == "__main__":
    app()
