<div align="center">

# 📊 Stock Analysis Tool

**A Python CLI that fetches historical stock data from Yahoo Finance,<br>computes a full suite of technical indicators, detects buy/sell signals,<br>and exports PDF reports, Excel workbooks, and publication-ready charts.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-F0B429?style=flat-square)](LICENSE)
[![yfinance](https://img.shields.io/badge/yfinance-Data-6C8EBF?style=flat-square)](https://github.com/ranaroussi/yfinance)
[![Typer](https://img.shields.io/badge/Typer-CLI-009485?style=flat-square)](https://typer.tiangolo.com/)
[![Rich](https://img.shields.io/badge/Rich-Terminal-AF5CF7?style=flat-square)](https://github.com/Textualize/rich)
[![pandas-ta](https://img.shields.io/badge/pandas--ta-Indicators-150458?style=flat-square&logo=pandas&logoColor=white)](https://github.com/twopirllc/pandas-ta)

</div>

---

## Table of Contents

- [📊 Stock Analysis Tool](#-stock-analysis-tool)
  - [Table of Contents](#table-of-contents)
  - [Overview](#overview)
  - [Features](#features)
  - [Project Structure](#project-structure)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Usage](#usage)
    - [Commands](#commands)
    - [`analyze`](#analyze)
    - [`list-indicators`](#list-indicators)
    - [Flags Reference](#flags-reference)
    - [Examples](#examples)
  - [Technical Indicators](#technical-indicators)
    - [Overlay Indicators](#overlay-indicators)
    - [Oscillator Indicators](#oscillator-indicators)
    - [Volatility Indicators](#volatility-indicators)
    - [Signal Detection](#signal-detection)
    - [Structural Indicators](#structural-indicators)
  - [Outputs](#outputs)
    - [PDF Report](#pdf-report)
    - [Excel Export](#excel-export)
    - [Chart Images](#chart-images)
  - [Date Range Behaviour](#date-range-behaviour)
  - [Logging](#logging)
  - [Module Overview](#module-overview)
  - [License](#license)

---

## Overview

Stock Analysis Tool is a fully featured command-line application for technical and fundamental stock analysis. It fetches historical OHLCV data from **Yahoo Finance** for any globally listed ticker, computes a configurable suite of indicators, and produces three types of output in a single command:

- A **multi-panel technical chart** with overlays, oscillators, buy/sell signal markers, and support/resistance levels
- A **structured PDF report** with per-ticker key statistics, fundamental data, and plain-English commentary
- A **formatted Excel workbook** with all OHLCV and indicator data, one sheet per ticker

The tool is built with [Typer](https://typer.tiangolo.com/) and [Rich](https://github.com/Textualize/rich) for a clean, professional terminal experience, and supports any ticker available on Yahoo Finance — including international exchanges such as ATHEX (`.AT` suffix).

---

## Features

| Feature | Description |
|---|---|
| 📡 **Live Data Fetching** | Downloads historical OHLCV data from Yahoo Finance via `yfinance` |
| 📐 **11 Technical Indicators** | Bollinger Bands, RSI, MACD, EMA 20/50/200, ATR, Stochastic, Volume |
| 🎯 **Signal Detection** | Buy/sell markers from RSI crossovers, MACD crossovers, and golden/death crosses |
| 📏 **Support & Resistance** | Auto-detected key price levels drawn directly on the chart |
| 🏦 **Fundamental Data** | P/E, market cap, 52W high/low, beta, EPS, revenue, sector via `--fundamentals` |
| 📊 **Comparison Chart** | Normalised relative performance across multiple tickers via `--compare` |
| 📄 **PDF Report** | Key stats table, fundamental data, plain-English commentary, embedded chart |
| 📁 **Excel Export** | Multi-sheet workbook with all OHLCV and indicator columns per ticker |
| 📅 **Preset Date Ranges** | `1m`, `3m`, `6m`, `1y`, `5y` shortcuts via `--period` |
| 🎛️ **Selective Indicators** | Run only the indicators you want using repeated `--indicator` flags |
| ⚙️ **Config File** | Set personal defaults in `config.yaml` — no retyping of common options |
| 🪵 **Structured Logging** | Console + persistent log file; `--verbose` for full debug output |

---

## Project Structure

```
TechnicalAnalysis/
│
├── main.py                   # CLI entry point (Typer app)
├── config.yaml               # Default settings (period, indicators)
├── requirements.txt
│
├── data/                     # All generated outputs (auto-created)
│   ├── stock_analysis_report.pdf
│   ├── stock_data.xlsx
│   ├── <TICKER>_analysis_plots.png
│   ├── comparison_chart.png
│   └── stocktool.log
│
└── utils/
    ├── __init__.py
    ├── analyzedata.py         # Indicator computation
    ├── cleandata.py           # OHLCV data validation and cleaning
    ├── comparison.py          # Multi-ticker normalised comparison chart
    ├── fetchstockdata.py      # yfinance data fetching
    ├── fundamentals.py        # Fundamental data + earnings dates
    ├── generatepdfreport.py   # PDF report generation
    ├── generateplots.py       # Dynamic multi-panel chart generation
    ├── savetoexcel.py         # Excel workbook export
    └── signals.py             # Signal detection + support/resistance
```

---

## Requirements

- **Python 3.11** or higher
- An internet connection (Yahoo Finance data is fetched at runtime)

| Package | Purpose |
|---|---|
| `yfinance` | Historical OHLCV and fundamental data from Yahoo Finance |
| `pandas` / `pandas-ta` | Data manipulation and technical indicator calculation |
| `mplfinance` / `matplotlib` | Candlestick charts and multi-panel figure rendering |
| `fpdf` | PDF report generation |
| `openpyxl` | Excel workbook creation and export |
| `typer[all]` | CLI framework with argument parsing and help generation |
| `rich` | Terminal formatting, progress spinners, and tables |
| `PyYAML` | `config.yaml` parsing |
| `python-dateutil` | Relative date arithmetic for period presets |

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/your-username/TechnicalAnalysis.git
cd TechnicalAnalysis
```

**2. Create and activate a virtual environment** *(recommended)*

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Verify the installation**

```bash
python main.py --help
```

You should see the Typer help output listing the available commands.

---

## Configuration

All default behaviour is controlled by **`config.yaml`** in the project root. Any flag passed on the command line takes precedence over the config file.

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

If `config.yaml` is absent, all indicators are enabled and the period defaults to `1y`.

---

## Usage

All functionality is accessed through `main.py`. The tool uses a subcommand structure:

```
python main.py [COMMAND] [OPTIONS]
```

### Commands

| Command | Description |
|---|---|
| `analyze` | Fetch, analyse, and report on one or more tickers |
| `list-indicators` | Display all available indicators with descriptions |

---

### `analyze`

The primary command. Fetches data for each ticker, computes the selected indicators, generates charts, and writes all outputs.

```bash
python main.py analyze [OPTIONS]
```

### `list-indicators`

Prints a formatted table of all supported indicator keys, their full names, and descriptions. Use this to look up the exact key strings required by `--indicator`.

```bash
python main.py list-indicators
```

---

### Flags Reference

| Flag | Short | Type | Default | Description |
|---|---|---|---|---|
| `--tickers` | `-t` | `str` | **Required** | Comma-separated ticker symbols, e.g. `AAPL,TSLA,NVDA` |
| `--start` | `-s` | `str` | Derived from `--period` | Start date in `YYYY-MM-DD` format |
| `--end` | `-e` | `str` | Today | End date in `YYYY-MM-DD` format |
| `--period` | `-p` | `str` | `1y` (from config) | Preset range: `1m`, `3m`, `6m`, `1y`, `5y`. Ignored if `--start` is set |
| `--indicator` | `-i` | `str` (repeatable) | All indicators | Indicator key to include. Repeat the flag for multiple selections |
| `--compare` | `-c` | flag | `False` | Generate a normalised multi-ticker comparison chart |
| `--fundamentals` | `-f` | flag | `False` | Fetch and include fundamental data in the PDF report |
| `--no-pdf` | | flag | `False` | Skip PDF report generation |
| `--no-excel` | | flag | `False` | Skip Excel export |
| `--verbose` | `-v` | flag | `False` | Enable DEBUG-level logging to console and log file |

> **Note on `--indicator`:** The flag must be repeated once per indicator, e.g. `-i rsi -i macd`. Passing an unrecognised key prints the valid options and exits immediately.

---

### Examples

**Analyse a single ticker with all indicators over the past year (default)**
```bash
python main.py analyze -t AAPL
```

**Analyse over a specific preset period**
```bash
python main.py analyze -t TSLA --period 6m
python main.py analyze -t MSFT --period 3m
python main.py analyze -t NVDA --period 5y
```

**Use an explicit date range**
```bash
python main.py analyze -t AAPL --start 2024-01-01 --end 2024-12-31
```

**Use an explicit start date with today as the end date**
```bash
python main.py analyze -t KARE.AT --start 2025-01-01
```

**Analyse multiple tickers simultaneously**
```bash
python main.py analyze -t AAPL,MSFT,GOOG,NVDA
```

**Include a normalised comparison chart** *(requires 2+ tickers)*
```bash
python main.py analyze -t AAPL,TSLA,NVDA --compare
```

**Include fundamental data in the PDF report**
```bash
python main.py analyze -t AAPL --fundamentals
```

**Full analysis with comparison and fundamentals**
```bash
python main.py analyze -t AAPL,MSFT,GOOG --period 1y --compare --fundamentals
```

**Select specific indicators only**
```bash
# RSI and MACD only
python main.py analyze -t AAPL -i rsi -i macd

# EMA trend analysis with signals
python main.py analyze -t TSLA -i ema50 -i ema200 -i signals

# Volatility-focused analysis
python main.py analyze -t SPY -i bollinger -i atr -i volume
```

**Skip specific outputs**
```bash
python main.py analyze -t AAPL --no-pdf          # chart + Excel only
python main.py analyze -t AAPL --no-excel        # chart + PDF only
python main.py analyze -t AAPL --no-pdf --no-excel  # charts only
```

**Enable verbose debug logging**
```bash
python main.py analyze -t AAPL --verbose
```

**List all available indicators**
```bash
python main.py list-indicators
```

**Get help for any command**
```bash
python main.py --help
python main.py analyze --help
```

---

## Technical Indicators

All indicators are computed with [pandas-ta](https://github.com/twopirllc/pandas-ta) on cleaned OHLCV data. A **6-month warmup window** is silently fetched before your requested start date so that long-period indicators (EMA 200, MACD) are fully populated from the very first visible bar. Warmup rows are trimmed before any chart, report, or export is written.

### Overlay Indicators

Rendered directly on the candlestick price panel.

| Key | Name | Description |
|---|---|---|
| `bollinger` | Bollinger Bands | Upper and lower bands at 2 standard deviations from a 20-period SMA. Price near the upper band may be overbought; near the lower band oversold. Rendered as dashed purple lines. |
| `ema20` | EMA 20 | 20-period Exponential Moving Average — short-term trend reference. |
| `ema50` | EMA 50 | 50-period EMA — medium-term trend reference. |
| `ema200` | EMA 200 | 200-period EMA — the primary long-term benchmark used by institutional traders. |

### Oscillator Indicators

Rendered in a dedicated panel above the candlestick chart.

| Key | Name | Description |
|---|---|---|
| `rsi` | RSI (14) | Relative Strength Index over 14 periods. Above 70 is overbought; below 30 is oversold. Threshold lines are drawn automatically. |
| `stochastic` | Stochastic Oscillator | %K and %D momentum lines. Above 80 is overbought; below 20 is oversold. Overlaid on the RSI panel when both are active. |
| `macd` | MACD | MACD line (blue), signal line (orange), and a green/red histogram in a dedicated bottom panel. Histogram sign indicates whether momentum is expanding or contracting. |

### Volatility Indicators

| Key | Name | Description |
|---|---|---|
| `atr` | ATR (14) | Average True Range over 14 periods in price units — useful for sizing stop-losses and gauging day-to-day price movement. Rendered in its own panel. |
| `volume` | Volume | Daily volume bars coloured green on up days and red on down days. High-volume moves carry significantly more weight than low-volume ones. |

### Signal Detection

| Key | Name | Description |
|---|---|---|
| `signals` | Buy / Sell Signals | Triangle markers plotted on the price chart. **Buy ▲ (green):** RSI crossing back above 30, MACD crossing above its signal line, or EMA50 crossing above EMA200 (golden cross). **Sell ▼ (red):** RSI crossing back below 70, MACD crossing below its signal line, or EMA50 crossing below EMA200 (death cross). Multiple signals on the same bar are de-duplicated. |

### Structural Indicators

| Key | Name | Description |
|---|---|---|
| `support_resistance` | Support & Resistance | Up to 3 support levels (dotted green lines) and 3 resistance levels (dotted red lines), automatically detected from rolling window price extrema and drawn across the full price panel. |

---

## Outputs

All outputs are written to the `data/` directory, which is created automatically on first run.

### PDF Report

`data/stock_analysis_report.pdf`

| Section | Contents |
|---|---|
| Cover page | Generation timestamp, ticker list, and active indicators |
| Comparison chart | Normalised relative performance chart (only with `--compare` and 2+ tickers) |
| Key Statistics table | Latest close, period return, and current value of every active indicator |
| Fundamental Data table | P/E ratio, market cap, 52W high/low, beta, EPS, revenue, sector, industry (only with `--fundamentals`) |
| Technical Commentary | Plain-English paragraph summarising the current state of every active indicator |
| Technical Chart | Full multi-panel chart image embedded at full page width |

### Excel Export

`data/stock_data.xlsx`

A multi-sheet workbook with one sheet per ticker. Each sheet contains the full OHLCV data plus every computed indicator column, indexed by date. Suitable for further analysis directly in Excel.

### Chart Images

`data/<TICKER>_analysis_plots.png` — individual ticker charts  
`data/comparison_chart.png` — multi-ticker comparison (when `--compare` is used)

Charts are saved at 150 DPI and sized dynamically based on the number of active panels.

```
┌─────────────────────────────────────────┐
│  RSI / Stochastic                       │  ← oscillator panel
├─────────────────────────────────────────┤
│                                         │
│  Candlestick  ·  Bollinger Bands        │
│  EMA 20 / 50 / 200                      │  ← price panel (4x height)
│  Buy / Sell signal markers              │
│  Support & resistance levels            │
│                                         │
├─────────────────────────────────────────┤
│  Volume                                 │  ← volume panel
├─────────────────────────────────────────┤
│  MACD · Signal · Histogram              │  ← MACD panel
├─────────────────────────────────────────┤
│  ATR                                    │  ← ATR panel
└─────────────────────────────────────────┘
```

> Panels are created only for active indicators — disabling an indicator removes its panel entirely.

---

## Date Range Behaviour

Dates are resolved in the following order of precedence:

1. `--start` / `--end` flags — explicit dates always win
2. `--period` preset — used when `--start` is not provided
3. `period` key in `config.yaml`
4. Hard fallback of `1y`

| Flag combination | Result |
|---|---|
| `--start 2024-01-01` | 2024-01-01 to today |
| `--start 2024-01-01 --end 2024-06-30` | Explicit range |
| `--period 6m` | 6 months ago to today |
| `--period 6m --end 2024-12-31` | 6 months before 2024-12-31 |
| *(no flags)* | Reads `period` from `config.yaml`, default `1y` |

> ⚠️ **Warmup window:** An extra 6 months of data is always fetched silently before your start date. This ensures long-lookback indicators (EMA 200 needs ~200 bars; MACD needs ~35) are fully calculated from your first visible bar. Warmup rows never appear in charts, the PDF, or the Excel export.

---

## Logging

Logging writes simultaneously to the terminal and to `data/stocktool.log`.

| Mode | Level | Content |
|---|---|---|
| Normal | `INFO` | Progress messages, file save paths, and per-ticker warnings |
| Verbose (`-v`) | `DEBUG` | Indicator calculation details, signal counts, cleaned data shapes, all intermediate steps |

```bash
python main.py analyze -t AAPL --verbose
```

The log file persists between runs and appends continuously, making it useful for diagnosing issues after the fact.

---

## Module Overview

| Module | Responsibility |
|---|---|
| `main.py` | Typer CLI app, command routing, and orchestration of the full pipeline |
| `utils/fetchstockdata.py` | Downloads OHLCV data from Yahoo Finance, flattens MultiIndex columns |
| `utils/cleandata.py` | Coerces OHLCV columns to numeric, drops rows containing NaN |
| `utils/analyzedata.py` | Computes all technical indicators via `pandas-ta`; only requested indicators are calculated |
| `utils/signals.py` | Detects buy/sell crossover events; detects support and resistance levels from rolling extrema |
| `utils/fundamentals.py` | Fetches fundamental metrics and earnings calendar from `yfinance.Ticker.info` |
| `utils/generateplots.py` | Builds a dynamic multi-panel `mplfinance` chart; panels are added only for active indicators |
| `utils/comparison.py` | Generates a normalised relative performance line chart across multiple tickers |
| `utils/generatepdfreport.py` | Assembles the full PDF report: tables, commentary, and embedded chart images |
| `utils/savetoexcel.py` | Writes all ticker DataFrames to a multi-sheet Excel workbook |

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <sub>Data sourced from <a href="https://finance.yahoo.com">Yahoo Finance</a> via <a href="https://github.com/ranaroussi/yfinance">yfinance</a></sub>
</div>