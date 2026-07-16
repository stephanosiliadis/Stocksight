# Stocksight

A Streamlit web application for interactive stock analysis featuring real-time
technical charting, financial statements, backtesting, PDF/Excel export, and
Google News integration. Built with pandas, pandas-ta, Plotly, and yfinance.

[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.59.1%2B-FF6C6C?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![uv](https://img.shields.io/badge/uv-package%20manager-6E56CF?style=flat-square)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-F0B429?style=flat-square)](LICENSE)
[![yfinance](https://img.shields.io/badge/yfinance-Data-6C8EBF?style=flat-square)](https://github.com/ranaroussi/yfinance)
[![pandas-ta](https://img.shields.io/badge/pandas--ta-Indicators-150458?style=flat-square&logo=pandas&logoColor=white)](https://github.com/twopirllc/pandas-ta)
[![Plotly](https://img.shields.io/badge/Plotly-Charts-003366?style=flat-square)](https://plotly.com/)
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

Stocksight is a web-based stock analysis platform built with Streamlit. It
provides an intuitive interactive interface for analyzing stock performance,
generating trading signals, backtesting strategies, and viewing the latest
financial news. Users can analyze single or multiple tickers simultaneously,
compare normalized performance, and export detailed reports.

**Key features:**

- Multi-ticker analysis with synchronized controls
- 11+ technical indicators with dynamic chart panels
- Signal-driven backtesting with performance metrics
- Real-time Google News integration filtered for stock-related articles
- PDF reports with embedded charts and financial statements
- Excel export with per-ticker sheets and summary statistics
- Intelligent caching system for performance optimization
- Normalized comparison charts for multi-ticker analysis

The tool connects to Yahoo Finance for historical OHLCV data and fundamental
metrics, computes indicators via `pandas-ta`, and renders interactive charts
with Plotly.

---

## Features

| Feature                  | Description                                                                                      |
| ------------------------ | ------------------------------------------------------------------------------------------------ |
| Web UI with Streamlit    | Interactive sidebar controls with real-time updates and tab-based navigation.                    |
| Multi-ticker tabs        | Analyze multiple tickers simultaneously with individual analysis tabs.                           |
| Live stock data          | Historical OHLCV data from Yahoo Finance via `yfinance`.                                         |
| 11+ technical indicators | Bollinger Bands, RSI, MACD, EMA 20/50/200, ATR, Stochastic, Volume with dynamic panel rendering. |
| Signal detection         | Buy/sell markers from RSI crossings, MACD crossovers, and EMA golden/death crosses.              |
| Support and resistance   | Auto-detected from rolling-window extrema and drawn on interactive charts.                       |
| Fundamentals             | P/E, market cap, 52W high/low, beta, EPS, revenue, sector, industry.                             |
| Financial statements     | Income statement, balance sheet, and cash flow integration.                                      |
| Signal-driven backtest   | Long-only strategy with total return, buy-and-hold, alpha, win rate, max drawdown, Sharpe ratio. |
| Comparison chart         | Normalized relative-performance chart across multiple tickers.                                   |
| News integration         | Top 3 stock-related articles from Google News per ticker with intelligent filtering.             |
| Intelligent caching      | Incremental data fetching with overlap detection for improved performance.                       |
| PDF report               | Key stats, fundamentals, statements, backtest results with embedded interactive charts.          |
| Excel export             | One sheet per ticker plus a Summary sheet with high/low/drawdown statistics.                     |
| Flexible date ranges     | Sidebar date picker for custom analysis periods.                                                 |
| Selective indicators     | Toggle indicators on/off in real-time for focused analysis.                                      |
| Interactive charts       | Plotly-based multi-panel candlestick charts with hover tooltips and signals.                     |

---

## Project Structure

```
Stocksight/
  main.py                      # Streamlit entry point
  config.yaml                  # Configuration (period, indicators)
  pyproject.toml               # Project metadata and dependencies
  uv.lock                      # Resolved dependency lockfile
  .python-version              # Pinned Python version
  LICENSE                      # MIT license
  README.md                    # This file

  assets/
    styles.css                 # Custom styling

  cache/                       # Runtime caches
    selected_tickers.json      # Persisted user ticker selection
    fundamentals/              # Cached fundamental data
    prices/                    # Cached price data
    statements/                # Cached financial statements

  src/
    __init__.py
    components/                # Streamlit UI components
      __init__.py
      backtest_panel.py        # Backtest results display
      charts.py                # Chart rendering components
      date_selector.py         # Date range picker
      financials_panel.py      # Financial statements display
      fundamentals_panel.py    # Fundamentals display
      indicator_selector.py    # Indicator toggle panel
      metrics_cards.py         # Statistics cards
      news_panel.py            # News articles display
      ticker_input.py          # Ticker input component

    models/                    # Pydantic data models
      __init__.py
      analysis_request.py      # Analysis parameters
      analysis_result.py       # Analysis output
      backtest_result.py       # Backtest metrics
      financial_statements.py  # Statement data
      fundamentals.py          # Fundamental metrics
      signal.py                # Signal data
      statistics.py            # Statistical metrics
      trade.py                 # Backtest trade

    pages/                     # Streamlit pages
      __init__.py
      backtesting.py           # Backtest page (if separate)
      comparison.py            # Comparison page (if separate)
      dashboard.py             # Dashboard page (if separate)
      settings.py              # Settings page
      stock_analysis.py        # Main analysis page
      watchlists.py            # Watchlist page (if available)

    services/                  # Business logic services
      __init__.py
      analysis_service.py      # Orchestrates analysis pipeline
      backtest_service.py      # Backtesting engine
      comparison_service.py    # Comparison logic
      data_service.py          # Data fetching from yfinance
      financials_service.py    # Financial statements fetching
      fundamentals_service.py  # Fundamentals fetching
      indicator_service.py     # Technical indicator calculation
      signal_service.py        # Signal generation
      statistics_service.py    # Statistics computation

    tests/                     # Test modules
      test_backtest.py
      test_fetching.py
      test_indicators.py
      test_signals.py
      test_validators.py

    utils/                     # Utility modules
      __init__.py
      cache.py                 # Intelligent caching system
      data_cleaner.py          # OHLCV data cleaning
      data_fetcher.py          # Data fetching utilities
      dates.py                 # Date utilities
      helpers.py               # Helper functions
      news_fetcher.py          # Google News RSS fetching
      validators.py            # Input validation

    visualization/             # Chart rendering
      __init__.py
      chart_theme.py           # Chart styling
      comparison_chart.py      # Comparison chart builder
      indicator_plots.py       # Indicator-specific plots
      technical_chart.py       # Main technical chart
```

---

## Requirements

- **Python 3.13** or higher (pinned in `.python-version`)
- **uv** for dependency management (recommended) -- <https://github.com/astral-sh/uv>
- An internet connection (Yahoo Finance data is fetched at runtime)

### Runtime dependencies

| Package           | Purpose                                                               |
| ----------------- | --------------------------------------------------------------------- |
| `streamlit`       | Web UI framework for interactive analysis                             |
| `yfinance`        | Historical OHLCV, fundamental data, and statements from Yahoo Finance |
| `pandas`          | Data manipulation and analysis                                        |
| `pandas-ta`       | Technical indicator calculation                                       |
| `numpy`           | Numerical primitives used by indicators                               |
| `plotly`          | Interactive multi-panel charting                                      |
| `fpdf2`           | PDF report generation                                                 |
| `openpyxl`        | Excel workbook creation and export                                    |
| `requests`        | HTTP requests for data fetching                                       |
| `PyYAML`          | `config.yaml` parsing                                                 |
| `python-dateutil` | Date arithmetic and manipulation                                      |

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

3. **Run the application**

   ```bash
   uv run main.py
   ```

   The Streamlit app will launch in your default browser at `http://localhost:8501`.

4. **Verify the installation** (optional)

   ```bash
   uv run python -c "import streamlit; import yfinance; print('✓ Installation successful')"
   ```

---

## Configuration

The application uses **`config.yaml`** for default settings. Any selection
made in the Streamlit UI overrides the config file.

```yaml
# config.yaml

defaults:
  # Default date range preset (1m | 3m | 6m | 1y | 5y)
  period: "1y"

  # Indicators enabled by default. Comment out any you don't want.
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

  # Directory for output files
  output_dir: "data"
```

If `config.yaml` is missing, all indicators are enabled by default and the
period defaults to `1y`.

---

## Usage

### Starting the Application

```bash
uv run main.py
```

The Streamlit web interface will launch automatically in your default browser
at `http://localhost:8501`.

### Interface Overview

**Sidebar Controls:**

- **Ticker Input**: Enter one or more tickers (comma-separated)
- **Date Selector**: Choose date range using preset periods (1m, 3m, 6m, 1y, 5y) or custom dates
- **Indicator Selector**: Toggle technical indicators on/off for focused analysis
- **Backtest Controls**: Enable backtesting and set initial capital
- **Analysis Button**: Run the analysis with current settings

**Main Content Area:**

- **Analysis Tabs**: One tab per ticker showing technical charts, statistics, and financial data
- **Comparison Tab**: Normalized performance comparison across selected tickers
- **News Tab**: Top 3 stock-related articles from Google News per ticker
- **Export Buttons**: Download PDF reports and Excel workbooks

### Workflow

1. **Enter Tickers**: Input stock symbols in the ticker input box (e.g., `AAPL`, `MSFT,TSLA`)

2. **Select Date Range**: Use sidebar presets (1m/3m/6m/1y/5y) or pick custom start/end dates

3. **Choose Indicators**: Toggle desired technical indicators (Bollinger Bands, RSI, MACD, EMAs, etc.)

4. **Optional Features**:
   - Enable backtest with starting capital
   - Charts display signals and support/resistance levels
   - Fundamentals and financial statements are auto-fetched

5. **View Results**:
   - Individual ticker tabs show candlestick charts with overlays and indicators
   - Comparison tab displays normalized relative performance
   - News tab shows latest Google News articles filtered for stock relevance
   - Statistics cards show key metrics

6. **Export**: Download PDF reports with embedded charts or Excel workbooks with all data

### Example Analyses

**Single Ticker - Technical Focus**

- Enter: `AAPL`
- Period: `6m` (6 months)
- Indicators: EMA 20/50/200, RSI, MACD, Signals
- Result: Trend analysis with support/resistance

**Multi-Ticker Comparison**

- Enter: `AAPL,MSFT,GOOG,NVDA`
- Period: `1y` (1 year)
- Enable: Comparison tab
- Result: Normalized performance comparison across tech stocks

**Strategy Backtesting**

- Enter: `TSLA`
- Period: `1y`
- Enable: Backtest with $10,000 initial capital
- Result: Win rate, Sharpe ratio, drawdown, and complete trade log

---

## Input Validation

All user inputs are validated before any data is fetched or analysis begins.
Invalid inputs result in clear error messages displayed in the Streamlit UI.

| Input            | Validation                                            | Behaviour                                    |
| ---------------- | ----------------------------------------------------- | -------------------------------------------- |
| Tickers          | Non-empty, valid format (letters or letters.letters)  | Rejects empty, invalid, or duplicate tickers |
| Date range       | Valid `YYYY-MM-DD` format, end ≥ start, not in future | Rejects malformed dates or invalid ranges    |
| Indicators       | At least one selected                                 | Warns if no indicators are chosen            |
| Backtest capital | Positive number                                       | Rejects zero or negative values              |
| Period preset    | Valid value (1m, 3m, 6m, 1y, 5y)                      | Uses config default if invalid               |

---

## Technical Indicators

All indicators are computed with [pandas-ta](https://github.com/twopirllc/pandas-ta)
on cleaned OHLCV data. A **12-month warmup window** is silently fetched before
the requested start date to ensure long-lookback indicators (EMA 200, MACD) are
fully populated from the first visible bar. Warmup rows are trimmed before any
display or export.

### Overlay Indicators

Rendered directly on the candlestick price panel.

| Key         | Name            | Description                                                          |
| ----------- | --------------- | -------------------------------------------------------------------- |
| `bollinger` | Bollinger Bands | Upper and lower bands at 2 standard deviations from a 20-period SMA. |
| `ema20`     | EMA 20          | 20-period Exponential Moving Average -- short-term trend.            |
| `ema50`     | EMA 50          | 50-period EMA -- medium-term trend.                                  |
| `ema200`    | EMA 200         | 200-period EMA -- long-term benchmark.                               |

### Oscillator Indicators

Rendered in dedicated panels.

| Key          | Name                  | Description                                                                         |
| ------------ | --------------------- | ----------------------------------------------------------------------------------- |
| `rsi`        | RSI (14)              | Relative Strength Index over 14 periods. Above 70 is overbought, below 30 oversold. |
| `stochastic` | Stochastic Oscillator | %K and %D momentum lines. Above 80 is overbought, below 20 oversold.                |
| `macd`       | MACD                  | Moving Average Convergence Divergence with signal line and histogram.               |

### Volatility and Volume

| Key      | Name     | Description                            |
| -------- | -------- | -------------------------------------- |
| `atr`    | ATR (14) | Average True Range over 14 periods.    |
| `volume` | Volume   | Bar chart coloured by price direction. |

### Signal Detection

| Key       | Name               | Description                                                                                              |
| --------- | ------------------ | -------------------------------------------------------------------------------------------------------- |
| `signals` | Buy / Sell Signals | Markers placed on candlesticks. Sources: RSI crosses (30/70), MACD crossovers, EMA golden/death crosses. |

### Structural Indicators

| Key                  | Name                   | Description                                                                            |
| -------------------- | ---------------------- | -------------------------------------------------------------------------------------- |
| `support_resistance` | Support and Resistance | Three top support and resistance levels detected from rolling extrema (20-bar window). |

---

## Outputs

All output files can be downloaded directly from the Streamlit interface
using the export buttons at the bottom of the analysis page.

### PDF Report

A comprehensive PDF report for each ticker including:

- Per-ticker key statistics table (period high/low, current close, drawdown)
- Fundamental data table (if available)
- Income statement, balance sheet, and cash flow (if fetched)
- Multi-panel technical chart with all selected indicators
- Backtest summary and trade log (if enabled)
- Comparison chart (if multiple tickers analyzed)

### Excel Export

A multi-sheet Excel workbook containing:

- **Summary** sheet: One row per ticker with period high, high date, low, low date, current close, % from high, % from low
- **Per-ticker sheets**: Full cleaned OHLCV data with all computed indicator columns

### Interactive Charts

All charts are built with Plotly and support:

- Hover tooltips with OHLCV, indicator values, and signal information
- Pan and zoom functionality
- Signal markers displayed on candlesticks
- Support/resistance levels as horizontal lines
- Multiple indicator panels with independent y-axes

### News Articles

The News tab displays:

- Top 3 stock-related articles per ticker from Google News
- Article titles (linked to source)
- Publication source and date
- Filtered for stock/financial relevance

## Caching System

Stocksight features an intelligent caching layer that optimizes performance
when analyzing overlapping date ranges.

### How It Works

The `AnalysisCache` class detects overlaps between cached data and new requests:

- **Full cache hit**: If the requested date range is fully cached, no new data
  is fetched.
- **Partial overlap**: If there's a partial match, only the missing date range
  is fetched and merged with cached data.
- **No cache**: If no cached data exists, the full range is fetched.

### Example

- **First request**: AAPL from 2025-01-01 to 2025-06-01 (fetches and caches)
- **Second request**: AAPL from 2025-01-01 to 2025-07-01 (reuses cached data, fetches only 2025-06-01 to 2025-07-01)

### Cache Scope

Cache is maintained per-ticker for the duration of the Streamlit session.
Caching includes:

- Raw OHLCV data
- Calculated indicators
- Generated trading signals

This significantly reduces API calls when performing multiple analyses on the
same ticker with overlapping periods.

---

## Logging

Application logs are written to the console and optionally to persistent log
files during development.

| Level   | Content                                                                                        |
| ------- | ---------------------------------------------------------------------------------------------- |
| `INFO`  | Data fetch progress, analysis completion, cache hits/misses                                    |
| `DEBUG` | Indicator calculations, signal detection, cache decisions (enable with `--logger.level=debug`) |
| `ERROR` | Network failures, data processing errors, validation failures                                  |

Debug logging can be enabled via Streamlit's logger configuration if needed
for troubleshooting.

---

## Architecture Overview

Stocksight uses a **service-oriented architecture** with clear separation of
concerns:

### Components Layer (`src/components/`)

Streamlit UI elements that render interactive controls and displays:

- Ticker input box with validation
- Date selector with preset and custom range options
- Indicator toggle switches
- Metrics cards for statistics display
- Financial statements panels
- Backtest results display
- News article list with links

### Services Layer (`src/services/`)

Business logic orchestrated through specialized services:

| Service                   | Responsibility                                                                       |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `analysis_service.py`     | Orchestrates full analysis pipeline; manages caching; coordinates all other services |
| `data_service.py`         | Fetches OHLCV data from Yahoo Finance; handles data cleaning                         |
| `indicator_service.py`    | Computes all technical indicators via pandas-ta                                      |
| `signal_service.py`       | Detects buy/sell signals from indicators; finds support/resistance levels            |
| `backtest_service.py`     | Runs signal-driven backtest; calculates performance metrics                          |
| `statistics_service.py`   | Computes period high/low, current close, drawdown, etc.                              |
| `fundamentals_service.py` | Fetches valuation metrics and fundamental data                                       |
| `financials_service.py`   | Fetches income statement, balance sheet, cash flow                                   |
| `comparison_service.py`   | Generates normalized multi-ticker comparison data                                    |

### Models Layer (`src/models/`)

Pydantic data classes for type-safe data flow:

- `AnalysisRequest`: User input parameters
- `AnalysisResult`: Full analysis output
- `BacktestResult`: Backtest metrics and trade log
- `Signal`, `Trade`: Event data structures
- `Statistics`, `Fundamentals`, `FinancialStatements`: Data containers

### Utilities Layer (`src/utils/`)

Helper modules for cross-cutting concerns:

- `cache.py`: Intelligent caching with overlap detection
- `data_cleaner.py`: OHLCV data validation and NaN handling
- `data_fetcher.py`: HTTP request utilities
- `news_fetcher.py`: Google News RSS fetching with filtering
- `validators.py`: Input validation for all user-facing data
- `dates.py`: Date arithmetic and formatting
- `helpers.py`: Miscellaneous utilities

### Visualization Layer (`src/visualization/`)

Plotly-based chart builders:

- `technical_chart.py`: Multi-panel chart with candlesticks, overlays, oscillators
- `comparison_chart.py`: Normalized relative-performance line chart
- `chart_theme.py`: Styling and color schemes

### Pages Layer (`src/pages/`)

Streamlit page definitions:

- `stock_analysis.py`: Main analysis interface with all controls and displays

### Data Flow

```
User Input (Sidebar)
    ↓
AnalysisService.analyze()
    ├→ AnalysisCache.get_cache_status()
    ├→ DataService.serve_stock_data()
    ├→ IndicatorService.serve_indicators()
    ├→ SignalService.serve_signals()
    ├→ StatisticsService.serve_statistics()
    ├→ BacktestService.serve_backtest() [optional]
    ├→ FundamentalsService.serve_fundamentals() [optional]
    ├→ FinancialsService.serve_financial_statements() [optional]
    └→ AnalysisCache.store_cache()
    ↓
AnalysisResult
    ├→ TechnicalChart.build() → Plotly Figure
    ├→ ComparisonChart.build() → Plotly Figure
    └→ PDFExporter / ExcelExporter → Files
    ↓
Streamlit UI Tabs + Downloads
```

---

## Roadmap and TODOs

### Recently Completed

- [x] Converted from CLI to Streamlit web interface
- [x] Multi-ticker analysis with synchronized tabs
- [x] Backtest integration with capital input
- [x] Comparison chart for multiple tickers
- [x] News articles tab with Google News integration
- [x] Intelligent caching system with overlap detection
- [x] PDF and Excel export with embedded charts

### High Priority

- [ ] Improve news filtering to eliminate non-financial articles more reliably
- [ ] Add session state persistence (save/load analysis configurations)
- [ ] Add watchlist functionality to save and load ticker groups
- [ ] Extend backtest with transaction costs, slippage, and position sizing
- [ ] Add risk metrics: volatility, beta, Sortino ratio, Value-at-Risk

### Analysis and Reporting

- [ ] Add portfolio-level summary across all analyzed tickers
- [ ] Add benchmark comparison (SPY, QQQ, or user-provided)
- [ ] Extend backtest with stop-loss, take-profit, max-position constraints
- [ ] Add dividend history and yield analysis
- [ ] Add valuation metrics: P/E trends, P/B, EV/EBITDA, FCF yield
- [ ] Include upcoming earnings dates in reports

### User Experience

- [ ] Add dark mode toggle
- [ ] Add indicator parameter customization (e.g., RSI period, Bollinger deviation)
- [ ] Add favorited tickers list in sidebar
- [ ] Add export templates with custom branding
- [ ] Add annotation tools for chart markup
- [ ] Improve mobile responsiveness

### Data and Performance

- [ ] Extend caching to persist between sessions (SQLite backend)
- [ ] Add retry and timeout configuration for network calls
- [ ] Normalize international ticker handling (document exchange suffixes)
- [ ] Add graceful handling for missing data (weekends, holidays)
- [ ] Add schema validation for OHLCV data quality

### Testing and Quality

- [ ] Add unit tests for services (data fetching, signal generation, backtest)
- [ ] Add integration tests with mocked yfinance responses
- [ ] Add tests for PDF and Excel export output
- [ ] Add regression tests for chart rendering
- [ ] Add static type checking (mypy) to CI

### Deployment and Distribution

- [ ] Add Streamlit Cloud deployment configuration
- [ ] Add Docker containerization
- [ ] Document deployment on VPS (Gunicorn + Streamlit)
- [ ] Add application versioning and release notes
- [ ] Add health checks and error monitoring

### Future Enhancements

- [ ] Add real-time price tickers in sidebar
- [ ] Add alerts for technical levels or signals
- [ ] Add sector and industry comparison views
- [ ] Add peer stock comparison within sectors
- [ ] Add advanced charting features (annotations, trend lines)
- [ ] Add option chain visualization (if data available)
- [ ] Add correlation matrix for multi-ticker analysis
- [ ] Add machine learning-based signal generation (experimental)
- [ ] Support alternative data providers (Alpha Vantage, IEX Cloud)

---

## License

This project is licensed under the **MIT License** -- see the
[LICENSE](LICENSE) file for details.

---

<sub>Data sourced from <https://finance.yahoo.com> via
[yfinance](https://github.com/ranaroussi/yfinance).</sub>
