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

# Use explicit date range, skip Excel output:
    python main.py analyze -t TSLA --start 2024-01-01 --end 2024-12-31 --no-excel

# List all available indicators:
    python main.py list-indicators
"""

import logging
import os
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

console = Console()

# ─── Typer app ────────────────────────────────────────────────────────────────
app = typer.Typer(
    name="stocktool",
    help="A CLI tool for comprehensive technical stock analysis.",
    add_completion=False,
)

# Preset period → months
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

    # ── Resolve tickers ───────────────────────────────────────────────────────
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]

    # ── Resolve dates ─────────────────────────────────────────────────────────
    effective_period = period or defaults.get("period", "1y")
    start_date, end_date = _resolve_dates(start, end, effective_period)

    # Fetch an extra 6-month warmup so long-period indicators (EMA200, MACD)
    # are fully populated from start_date onwards.
    warmup_start = (
        datetime.strptime(start_date, "%Y-%m-%d") - relativedelta(months=6)
    ).strftime("%Y-%m-%d")

    # ── Summary banner ────────────────────────────────────────────────────────
    console.rule("[bold cyan]Stock Analysis Tool[/bold cyan]")
    console.print(f"  Tickers   : [bold]{', '.join(ticker_list)}[/bold]")
    console.print(f"  Date range: {start_date} → {end_date}")
    console.print(f"  Indicators: {', '.join(active_indicators)}")
    console.print()

    # ── Per-ticker processing ─────────────────────────────────────────────────
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

            # Trim warmup rows
            trimmed = full_analysis[full_analysis.index >= start_date].copy()
            analyzed_data[ticker] = trimmed

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
        save_to_excel(analyzed_data, excel_path)
        console.print(f"  [green]✓[/green] Excel saved → {excel_path}")

    # ── PDF report ────────────────────────────────────────────────────────────
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
        console.print(f"  [green]✓[/green] PDF saved → {pdf_path}")

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


if __name__ == "__main__":
    app()
