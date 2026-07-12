# Stocksight

A Python CLI that fetches historical stock data from Yahoo Finance, computes a
configurable suite of technical indicators, detects buy/sell signals, and
exports PDF reports, Excel workbooks, and publication-ready charts.

[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/uv-package%20manager-6E56CF?style=flat-square)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-F0B429?style=flat-square)](LICENSE)
[![yfinance](https://img.shields.io/badge/yfinance-Data-6C8EBF?style=flat-square)](https://github.com/ranaroussi/yfinance)
[![Typer](https://img.shields.io/badge/Typer-CLI-009485?style=flat-square)](https://typer.tiangolo.com/)
[![Rich](https://img.shields.io/badge/Rich-Terminal-AF5CF7?style=flat-square)](https://github.com/Textualize/rich)
[![pandas-ta](https://img.shields.io/badge/pandas--ta-Indicators-150458?style=flat-square&logo=pandas&logoColor=white)](https://github.com/twopirllc/pandas-ta)
[![mplfinance](https://img.shields.io/badge/mplfinance-Charts-1f77b4?style=flat-square)](https://github.com/matplotlib/mplfinance)
[![fpdf2](https://img.shields.io/badge/fpdf2-PDF-d62728?style=flat-square)](https://py-pdf.github.io/fpdf2/)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Interactive Mode](#interactive-mode)
  - [Commands](#commands)
  - [`analyze`](#analyze)
  - [`list-indicators`](#list-indicators)
  - [Flags Reference](#flags-reference)
  - [Examples](#examples)
- [Input Validation](#input-validation)
- [Technical Indicators](#technical-indicators)
- [Outputs](#outputs)
- [Date Range Behaviour](#date-range-behaviour)
- [Building as a Standalone Executable](#building-as-a-standalone-executable)
- [Logging](#logging)
- [Module Overview](#module-overview)
- [Roadmap and TODOs](#roadmap-and-todos)
- [License](#license)

---

## Overview

Stocksight is a command-line application for technical and fundamental stock
analysis. It fetches historical OHLCV data from **Yahoo Finance** for any
globally listed ticker, computes a configurable suite of indicators via
`pandas-ta`, and produces several output artefacts in a single run:

- a multi-panel technical chart with overlays, oscillators, buy/sell signal
  markers, and support/resistance levels;
- a structured PDF report with per-ticker key statistics, fundamental data,
  plain-English commentary, and optional financial statements and backtest
  results;
- a formatted Excel workbook with a per-ticker sheet plus a summary sheet
  showing historical high/low and drawdown for the selected date range;
- a normalised multi-ticker comparison chart (when requested).

The tool is built with [Typer](https://typer.tiangolo.com/) and
[Rich](https://github.com/Textualize/rich) for a clean terminal experience and
supports any ticker available on Yahoo Finance, including international
exchanges such as ATHEX (`.AT` suffix). It can be driven by command-line
flags for scripting, or by a guided interactive menu that launches
automatically when the tool is started with no arguments.

---

## Features

| Feature | Description |
| --- | --- |
| Interactive mode | Step-by-step menu that launches when no flags are given, with back/cancel support at every prompt. |
| Pre-flight input validation | Dates, ticker format, period, indicator keys, and backtest capital are checked before any network call. |
| Live data fetching | Historical OHLCV data from Yahoo Finance via `yfinance`. |
| 11 technical indicators | Bollinger Bands, RSI, MACD, EMA 20/50/200, ATR, Stochastic, Volume, plus signal markers and support/resistance. |
| Signal detection | Buy/sell markers from RSI crossings, MACD crossovers, and EMA golden/death crosses. |
| Support and resistance | Auto-detected from rolling-window extrema and drawn on the chart. |
| Fundamentals | P/E, market cap, 52W high/low, beta, EPS, revenue, sector, industry via `--fundamentals`. |
| Financial statements | Income statement, balance sheet, and cash flow via `--statements`. |
| Signal-driven backtest | Long-only strategy with total return, buy-and-hold, alpha, win rate, max drawdown, Sharpe, and a full trade log via `--backtest`. |
| Comparison chart | Normalised relative-performance chart across multiple tickers via `--compare`. |
| PDF report | Key stats, fundamentals, statements, commentary, backtest results, and the embedded chart. |
| Excel export | One sheet per ticker plus a `Summary` sheet with high/low/drawdown stats. |
| Preset date ranges | `1m`, `3m`, `6m`, `1y`, `5y` shortcuts via `--period`. |
| Selective indicators | Run only the indicators you want using repeated `--indicator` flags. |
| Config file | Defaults in `config.yaml` -- any flag or interactive input takes precedence. |
| Standalone executable | Ships as a single file via PyInstaller; no Python required at runtime. |
| Structured logging | Console and persistent `data/stocktool.log`; `--verbose` for full debug output. |

---

## Project Structure

```
Stocksight/
  main.py                      # CLI entry point (Typer app + interactive menu)
  config.yaml                  # Default settings (period, indicators)
  pyproject.toml               # Project metadata and dependencies
  uv.lock                      # Resolved dependency lockfile
  Stocksight.spec              # PyInstaller build spec
  icon.ico                     # Executable icon
  .python-version              # Pinned Python version
  LICENSE                      # MIT license

  data/                        # All generated outputs (auto-created)
    stock_analysis_report.pdf
    stock_data.xlsx
    <TICKER>_analysis_plots.png
    comparison_chart.png
    stocktool.log

  utils/
    __init__.py
    analyzedata.py             # Indicator computation (pandas-ta)
    backtest.py                # Long-only signal-driven backtester
    cleandata.py               # OHLCV coercion and NaN handling
    comparison.py              # Multi-ticker normalised comparison chart
    fetchstockdata.py          # yfinance data fetching
    financials.py              # Income statement, balance sheet, cash flow
    fundamentals.py            # Valuation metrics and earnings calendar
    generatepdfreport.py       # PDF report assembly
    generateplots.py           # Dynamic multi-panel chart generation
    savetoexcel.py             # Multi-sheet Excel export
    signals.py                 # Buy/sell detection + support/resistance
    stats.py                   # Historical high/low range statistics
    validators.py              # Pre-flight input validation
```

---

## Requirements

- **Python 3.13** or higher (pinned in `.python-version`)
- **uv** for dependency management (recommended) -- <https://github.com/astral-sh/uv>
- An internet connection (Yahoo Finance data is fetched at runtime)

### Runtime dependencies

| Package | Purpose |
| --- | --- |
| `yfinance` | Historical OHLCV, fundamental data, and statements from Yahoo Finance |
| `pandas` | Data manipulation |
| `pandas-ta` | Technical indicator calculation |
| `numpy` | Numerical primitives used by indicators and signals |
| `mplfinance`, `matplotlib` | Candlestick charts and multi-panel figure rendering |
| `fpdf2` | PDF report generation |
| `openpyxl` | Excel workbook creation and export |
| `typer` | CLI framework with argument parsing and help generation |
| `rich` | Terminal formatting, progress spinners, interactive prompts, and tables |
| `PyYAML` | `config.yaml` parsing |
| `python-dateutil` | Relative date arithmetic for period presets |
| `pyinstaller` | Build-time dependency for the standalone executable |

All dependencies are pinned in `pyproject.toml` and resolved in `uv.lock`.

---

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/stephanosiliadis/Stocksight.git
   cd Stocksight
   ```

2. **Create a virtual environment and install dependencies** with `uv`

   ```bash
   uv sync
   ```

   This creates `.venv/` and installs the exact versions from `uv.lock`.

3. **Verify the installation**

   ```bash
   uv run python main.py --help
   ```

   You should see the Typer help output listing the available commands.

---

## Configuration

All default behaviour is controlled by **`config.yaml`** in the project root.
Any flag passed on the command line (or input entered in the interactive
menu) takes precedence over the config file.

```yaml
# config.yaml

defaults:
  # Default date range preset (1m | 3m | 6m | 1y | 5y)
  period: "1y"

  # Indicators to run when --indicator is not specified.
  # Comment out any you don't want by default.
  indicators:
    - bollinger
    - rsi
    - macd
    - ema20
    - ema50
    - ema200
    - volume
    - atr
    - stochastic
    - signals
    - support_resistance

  # Directory for all output files
  output_dir: "data"
```

If `config.yaml` is absent, all indicators are enabled and the period
defaults to `1y`. Output files are always written to the `data/` directory
in the current working directory (the `output_dir` key is currently
informational and not yet wired into the runtime).

---

## Usage

All functionality is accessed through `main.py`. The tool supports two usage
modes:

```bash
uv run python main.py                        # Interactive menu (guided)
uv run python main.py [COMMAND] [OPTIONS]    # Flag-driven (scripting / automation)
```

When `main.py` is run with no arguments, the interactive menu launches
automatically. The same is true when the bundled executable is
double-clicked.

### Interactive Mode

The interactive menu walks through every option step by step, validates each
input before moving on, and shows a configuration summary before running the
analysis. The full step list is:

1. Tickers (comma-separated)
2. Date mode: preset period or custom range
3. Period preset (`1m` / `3m` / `6m` / `1y` / `5y`) when applicable
4. Start date (when custom range selected)
5. End date (blank = today)
6. Indicator mode: all or selective
7. Indicators (when selective)
8. Comparison chart
9. Fundamentals
10. Financial statements
11. Backtest
12. Backtest starting capital (when backtest selected)
13. PDF report
14. Excel export
15. Verbose / debug logging
16. Confirmation

At any prompt, type `b` (or `back`) to revisit the previous step and `c`
(or `cancel`, `q`, `quit`) to abort the wizard entirely. Press `Enter` to
accept the default for the current step. Defaults are pre-filled from
`config.yaml` where applicable.

### Commands

| Command | Description |
| --- | --- |
| `analyze` | Fetch, analyse, and report on one or more stock tickers. |
| `list-indicators` | Print a table of all available indicator keys with descriptions. |

When invoked with no command and no flags, the interactive menu is launched
instead of `analyze`.

### `analyze`

Required: `--tickers` (or `-t`). All other flags are optional.

```bash
uv run python main.py analyze -t AAPL
uv run python main.py analyze -t AAPL,MSFT --period 6m --compare --fundamentals
```

### `list-indicators`

Prints a formatted table of every supported indicator key, its full name,
and a one-line description. Use this to look up the exact key strings
required by `--indicator`.

```bash
uv run python main.py list-indicators
```

### Flags Reference

| Flag | Short | Type | Default | Description |
| --- | --- | --- | --- | --- |
| `--tickers` | `-t` | `str` | required | Comma-separated ticker symbols, e.g. `AAPL,TSLA,NVDA`. |
| `--start` | `-sd` | `str` | Derived from `--period` | Start date in `YYYY-MM-DD` format. |
| `--end` | `-ed` | `str` | Today | End date in `YYYY-MM-DD` format. |
| `--period` | `-p` | `str` | `1y` (from `config.yaml`) | Preset range: `1m`, `3m`, `6m`, `1y`, `5y`. Ignored when `--start` is set. |
| `--indicator` | `-i` | `str` (repeatable) | All indicators | Indicator key to include. Repeat the flag for multiple. |
| `--compare` | `-c` | flag | `False` | Generate a normalised multi-ticker comparison chart (requires 2+ tickers). |
| `--fundamentals` | `-f` | flag | `False` | Fetch and include fundamental data in the report. |
| `--statements` | `-s` | flag | `False` | Fetch and include income statement, balance sheet, and cash flow. |
| `--backtest` | `-b` | flag | `False` | Run a signal-driven backtest and include results. Adds `signals` automatically. |
| `--capital` | | `float` | `10000.0` | Starting capital for the backtest. |
| `--no-pdf` | | flag | `False` | Skip PDF report generation. |
| `--no-excel` | | flag | `False` | Skip Excel export. |
| `--verbose` | `-v` | flag | `False` | Enable `DEBUG`-level logging on the console and log file. |

**Notes on flag behaviour**

- `--indicator` must be repeated once per indicator, e.g. `-i rsi -i macd`.
  Passing an unrecognised key prints the unknown keys and exits.
- `--backtest` automatically enables the `signals` indicator if it was not
  already selected.
- `--compare` is a no-op when fewer than two tickers produced data.

### Examples

**Single ticker with all indicators over the past year (default)**

```bash
uv run python main.py analyze -t AAPL
```

**Preset period**

```bash
uv run python main.py analyze -t TSLA --period 6m
uv run python main.py analyze -t MSFT --period 3m
uv run python main.py analyze -t NVDA --period 5y
```

**Explicit date range**

```bash
uv run python main.py analyze -t AAPL --start 2024-01-01 --end 2024-12-31
```

**Explicit start date with today as the end date**

```bash
uv run python main.py analyze -t KARE.AT --start 2025-01-01
```

**Multiple tickers simultaneously**

```bash
uv run python main.py analyze -t AAPL,MSFT,GOOG,NVDA
```

**Normalised comparison chart** (requires 2+ tickers)

```bash
uv run python main.py analyze -t AAPL,TSLA,NVDA --compare
```

**Fundamental data in the PDF report**

```bash
uv run python main.py analyze -t AAPL --fundamentals
```

**Full statements (income, balance sheet, cash flow)**

```bash
uv run python main.py analyze -t AAPL --statements
```

**Signal-driven backtest**

```bash
uv run python main.py analyze -t AAPL --backtest --capital 25000
```

**Full run with comparison, fundamentals, and backtest**

```bash
uv run python main.py analyze -t AAPL,MSFT,GOOG --period 1y \
    --compare --fundamentals --statements --backtest
```

**Select specific indicators only**

```bash
# RSI and MACD only
uv run python main.py analyze -t AAPL -i rsi -i macd

# EMA trend analysis with signals
uv run python main.py analyze -t TSLA -i ema50 -i ema200 -i signals

# Volatility-focused analysis
uv run python main.py analyze -t SPY -i bollinger -i atr -i volume
```

**Skip specific outputs**

```bash
uv run python main.py analyze -t AAPL --no-pdf          # chart + Excel only
uv run python main.py analyze -t AAPL --no-excel        # chart + PDF only
uv run python main.py analyze -t AAPL --no-pdf --no-excel  # charts only
```

**Enable verbose debug logging**

```bash
uv run python main.py analyze -t AAPL --verbose
```

**List all available indicators**

```bash
uv run python main.py list-indicators
```

**Get help for any command**

```bash
uv run python main.py --help
uv run python main.py analyze --help
```

---

## Input Validation

All inputs, whether provided via flags or the interactive menu, are
validated before any network request is made. The tool prints a clear
error and exits (or re-prompts in interactive mode) when any of the
following conditions fail.

| Condition | Behaviour |
| --- | --- |
| No tickers provided | "At least one ticker is required." |
| Ticker format invalid | Rejects strings that are not `letters` or `letters.letters` (e.g. `AAPL`, `SHOP.TO`). |
| Duplicate ticker | Rejected; duplicates must be removed before running. |
| Unknown `--period` value | Must be one of `1m`, `3m`, `6m`, `1y`, `5y`. |
| Invalid date format | Must be `YYYY-MM-DD`; anything else is rejected. |
| Start date in the future | Rejected. |
| End date in the future | Rejected. |
| End date before start date | Rejected. |
| Unknown indicator key | Rejected; the unknown keys are listed in the error message. |
| No indicators selected | "At least one indicator must be selected." |
| Non-positive backtest capital | Rejected. |
| Non-numeric backtest capital | Rejected. |

---

## Technical Indicators

All indicators are computed with
[pandas-ta](https://github.com/twopirllc/pandas-ta) on cleaned OHLCV data.
A **12-month warmup window** is silently fetched before the requested start
date so that long-lookback indicators (EMA 200, MACD) are fully populated
from the very first visible bar. Warmup rows are trimmed before any chart,
report, or export is written.

### Overlay indicators

Rendered directly on the candlestick price panel.

| Key | Name | Description |
| --- | --- | --- |
| `bollinger` | Bollinger Bands | Upper and lower bands at 2 standard deviations from a 20-period SMA. |
| `ema20` | EMA 20 | 20-period Exponential Moving Average -- short-term trend. |
| `ema50` | EMA 50 | 50-period EMA -- medium-term trend. |
| `ema200` | EMA 200 | 200-period EMA -- long-term benchmark. |

### Oscillator indicators

Rendered in a dedicated panel above the candlestick chart.

| Key | Name | Description |
| --- | --- | --- |
| `rsi` | RSI (14) | Relative Strength Index over 14 periods. Above 70 is overbought, below 30 oversold. Threshold lines drawn automatically. |
| `stochastic` | Stochastic Oscillator | %K and %D momentum lines. Above 80 is overbought, below 20 oversold. Overlaid on the same panel as RSI. |
| `macd` | MACD | Moving Average Convergence Divergence: MACD line, signal line, and histogram. Drawn in its own panel below the chart. |

### Volatility and volume

| Key | Name | Description |
| --- | --- | --- |
| `atr` | ATR (14) | Average True Range over 14 periods. Drawn in its own panel. |
| `volume` | Volume | Bar chart coloured by price direction. Drawn in its own panel. |

### Signal detection

| Key | Name | Description |
| --- | --- | --- |
| `signals` | Buy / Sell Signals | Markers placed just outside the candle. Sources: RSI crosses back above 30 (buy) or below 70 (sell), MACD line crosses above/below signal line, and EMA50/EMA200 golden/death crosses. Only one marker per bar (priority: RSI > MACD > EMA). |

### Structural indicators

| Key | Name | Description |
| --- | --- | --- |
| `support_resistance` | Support and Resistance | Three top support and three top resistance levels detected from rolling-window extrema (default window of 20 bars). Drawn as dotted horizontal lines on the price panel. |

### Panel layout

When all indicators are enabled, the chart has the following panels from top
to bottom (only panels for active indicators are created):

```
+----------------------------------------+
| RSI / Stochastic oscillator (optional) |
+----------------------------------------+
| Candlestick                           |
| Bollinger Bands, EMA 20/50/200        |  <- price panel
| Buy / Sell signal markers             |
| Support and resistance levels         |
+----------------------------------------+
| Volume (optional)                     |
+----------------------------------------+
| MACD (optional)                       |
+----------------------------------------+
| ATR (optional)                        |
+----------------------------------------+
```

Disabling an indicator removes its panel entirely.

---

## Outputs

All output files are written to the `data/` directory under the current
working directory.

### PDF report -- `data/stock_analysis_report.pdf`

A single PDF that includes, per ticker:

- a per-ticker key-statistics table (period high/low, drawdown, current close);
- fundamental data table (when `--fundamentals` is set);
- income statement, balance sheet, and cash flow (when `--statements` is set);
- plain-English technical commentary generated from the most recent bar;
- backtest summary and trade log (when `--backtest` is set);
- the per-ticker technical chart;
- the multi-ticker comparison chart (when `--compare` is set and 2+ tickers produced data).

### Excel export -- `data/stock_data.xlsx`

A multi-sheet workbook:

- a `Summary` sheet with one row per ticker containing period high, high date,
  period low, low date, current close, percentage from high, and percentage
  from low;
- one sheet per ticker with the full cleaned OHLCV data plus every computed
  indicator column.

### Chart images

- `data/<TICKER>_analysis_plots.png` -- the multi-panel technical chart for
  each ticker.
- `data/comparison_chart.png` -- the normalised comparison chart, when
  `--compare` is used with 2+ tickers.

### Log file

- `data/stocktool.log` -- persistent log file. Appends across runs.

---

## Date Range Behaviour

Dates are resolved in the following order of precedence:

1. `--start` / `--end` flags -- explicit dates always win.
2. `--period` preset -- used when `--start` is not provided.
3. `period` key in `config.yaml`.
4. Hard fallback of `1y`.

| Flag combination | Result |
| --- | --- |
| `--start 2024-01-01` | `2024-01-01` to today |
| `--start 2024-01-01 --end 2024-06-30` | Explicit range |
| `--period 6m` | 6 months ago to today |
| `--period 6m --end 2024-12-31` | 6 months before `2024-12-31` |
| *(no flags)* | Reads `period` from `config.yaml`, default `1y` |

> **Warmup window:** an extra 12 months of data is always fetched silently
> before the requested start date. This ensures long-lookback indicators
> (EMA 200 needs ~200 bars; MACD needs ~35) are fully calculated from the
> first visible bar. Warmup rows never appear in charts, the PDF, or the
> Excel export.

---

## Building as a Standalone Executable

The tool can be packaged into a single executable using
[PyInstaller](https://pyinstaller.org/). The repository ships a
`Stocksight.spec` that bundles `main.py`, the `config.yaml` data file, and
the application icon. The produced binary requires no Python installation
at runtime and can be launched by double-clicking (which triggers the
interactive menu) or from a terminal with flags.

**Build**

```bash
uv run pyinstaller Stocksight.spec
```

The output is written to `dist/`:

- Windows: `dist/Stocksight.exe`
- macOS / Linux: `dist/Stocksight`

**Run the executable**

```bash
# Interactive menu (double-click on Windows, or run with no arguments)
./dist/Stocksight

# Flag-driven, same as `uv run python main.py`
./dist/Stocksight analyze -t AAPL --period 6m
./dist/Stocksight list-indicators
```

**Notes on bundling**

- PyInstaller is already pinned in `pyproject.toml`; `uv sync` installs it
  into `.venv`.
- Data-heavy packages (`yfinance`, `pandas-ta`, `mplfinance`) pull in large
  transitive dependencies. The bundled executable is typically 100-200 MB.
- If PyInstaller misses a hidden import during a custom build, add it
  explicitly with `--hidden-import`.

---

## Logging

Logging writes simultaneously to the terminal and to
`data/stocktool.log`.

| Mode | Level | Content |
| --- | --- | --- |
| Normal | `INFO` | Progress messages, file save paths, per-ticker warnings. |
| Verbose (`-v`) | `DEBUG` | Indicator calculation details, signal counts, cleaned data shapes, all intermediate steps. |

```bash
uv run python main.py analyze -t AAPL --verbose
```

The log file persists between runs and appends continuously, making it
useful for diagnosing issues after the fact.

---

## Module Overview

| Module | Responsibility |
| --- | --- |
| `main.py` | Typer CLI app, interactive menu, input validation, and orchestration of the full pipeline. |
| `utils/fetchstockdata.py` | Downloads OHLCV data from Yahoo Finance; flattens MultiIndex columns. |
| `utils/cleandata.py` | Coerces OHLCV columns to numeric; drops rows containing NaN in critical columns. |
| `utils/analyzedata.py` | Computes all technical indicators via `pandas-ta`; only requested indicators are calculated. |
| `utils/signals.py` | Detects buy/sell crossover events; detects support and resistance levels from rolling extrema. |
| `utils/backtest.py` | Long-only signal-driven backtester; emits total return, buy-and-hold, alpha, win rate, max drawdown, Sharpe, and a full trade log. |
| `utils/stats.py` | Computes period high/low/current close/drawdown for the selected date range. |
| `utils/fundamentals.py` | Fetches fundamental metrics and earnings calendar from `yfinance.Ticker.info`. |
| `utils/financials.py` | Fetches and formats income statement, balance sheet, and cash flow. |
| `utils/generateplots.py` | Builds a dynamic multi-panel `mplfinance` chart; panels are added only for active indicators. |
| `utils/comparison.py` | Generates a normalised relative-performance line chart across multiple tickers. |
| `utils/generatepdfreport.py` | Assembles the full PDF report: tables, commentary, statements, backtest, and embedded chart images. |
| `utils/savetoexcel.py` | Writes all ticker DataFrames to a multi-sheet Excel workbook with a `Summary` sheet. |
| `utils/validators.py` | Pre-flight validators for tickers, dates, period, indicators, and backtest capital. |

---

## Roadmap and TODOs

### High priority

- [x] Add a back/cancel option to the interactive flow so users can revise
  an earlier answer without restarting the application.
- [x] Add historical high/low statistics for the selected date range and
  include them in the PDF report, Excel export, and terminal summary.
- [x] Validate empty ticker input, duplicate tickers, unsupported symbols,
  invalid date ranges, and unsupported period values before network
  requests are made.
- [x] Update the README so documented flags match the current CLI,
  including `--statements`, `--backtest`, `--capital`, and the actual
  short options.

### Analysis and reporting

- [ ] Add a portfolio-level summary across all analysed tickers: total
  return over the selected range, average drawdown from high, and distance
  from support and resistance.
- [ ] Extend the backtest module with transaction costs, slippage,
  configurable position sizing, stop-loss, take-profit, and max-position
  constraints.
- [ ] Add benchmark comparison support, such as comparing selected tickers
  against SPY, QQQ, or a user-provided benchmark ticker.
- [ ] Add risk metrics to reports: annualized volatility, beta versus
  benchmark, downside deviation, Sortino ratio, and value-at-risk.
- [ ] Include earnings dates and upcoming corporate events in the report
  when available from the data provider.
- [ ] Add optional CSV export for users who do not need a formatted Excel
  workbook.
- [ ] Add report metadata, including command arguments, data source
  timestamp, package version, and generated file paths.

### User experience

- [ ] Add an interactive review screen before execution that lets users
  edit tickers, date range, indicators, output choices, and analysis
  options.
- [ ] Add a saved-profile feature for common analysis setups, such as
  dividend stocks, growth stocks, index ETFs, or custom watchlists.
- [ ] Improve terminal output with a clear per-ticker status table showing
  fetched rows, generated indicators, warnings, and output paths.
- [ ] Add clearer help text for indicators, especially when indicators
  depend on other calculated columns.
- [ ] Add a `--output-dir` option so generated reports can be written
  outside the default `data/` directory.
- [ ] Add a `--watchlist` option that reads tickers from a text, CSV, or
  YAML file.

### Data and reliability

- [ ] Add a lightweight cache for downloaded price data and fundamentals
  to reduce repeated Yahoo Finance requests during development and batch
  runs.
- [ ] Add retry and timeout configuration for all network calls.
- [ ] Normalize ticker handling for international exchanges and document
  provider-specific suffix requirements.
- [ ] Preserve raw downloaded data separately from cleaned/analyzed data
  so data quality issues are easier to inspect.
- [ ] Add schema checks for required OHLCV columns before indicator
  calculation.
- [ ] Add graceful handling for missing volume, adjusted close,
  fundamentals, or statement rows.

### Testing and quality

- [ ] Add unit tests for date resolution, indicator selection, signal
  detection, support/resistance detection, and backtest calculations.
- [ ] Add integration tests that run a small analysis with mocked
  `yfinance` responses and verify expected PDF, Excel, and chart outputs
  are created.
- [ ] Add regression tests for PDF generation so sections remain present
  when fundamentals, statements, comparison, or backtests are enabled.
- [ ] Add static checks for formatting, imports, and type hints.
- [ ] Add CI that installs dependencies, runs tests, and builds the
  executable spec on every pull request.
- [ ] Add sample fixture data so tests do not depend on live market data.

### Packaging and distribution

- [ ] Add application versioning and expose it through `--version`.
- [ ] Add release notes or a changelog for user-facing changes.
- [ ] Confirm the packaged executable works on a clean Windows machine
  without a local Python installation.
- [ ] Add dependency pinning or a lock file to make installs and builds
  reproducible. *(lockfile is committed; document the workflow.)*

### Future enhancements

- [ ] Add a desktop or web UI for users who prefer not to work from the
  command line.
- [ ] Add alerts for price crossing moving averages, support/resistance
  levels, RSI thresholds, or new buy/sell signals.
- [ ] Add sector and industry comparison views for peer analysis.
- [ ] Add dividend history, dividend yield trends, and payout ratio
  analysis.
- [ ] Add valuation metrics such as price-to-sales, price-to-book,
  EV/EBITDA, free-cash-flow yield, and historical valuation ranges.
- [ ] Add export templates for professional report branding, including
  logo, color palette, and disclaimer text.
- [ ] Add support for alternative data providers to reduce dependency on a
  single source.
- [ ] Add a proper disclaimer section explaining that generated analysis
  is informational and not financial advice.

---

## License

This project is licensed under the **MIT License** -- see the
[LICENSE](LICENSE) file for details.

---

<sub>Data sourced from <https://finance.yahoo.com> via
[yfinance](https://github.com/ranaroussi/yfinance).</sub>
