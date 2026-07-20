# Stocksight -- Comprehensive Development Roadmap

_A day-by-day implementation guide: what to build, which files to create or modify, what each file needs to contain, and how it all connects._

---

## How to Use This Roadmap

This roadmap assumes the codebase conventions already established in Stocksight v1.0: Pydantic v2 models everywhere (with ConfigDict(arbitrary_types_allowed=True) on any model holding a pandas DataFrame); Signal/SignalType as the canonical contract between services; per-ticker try/except isolation in AnalysisService.analyze() so one bad ticker never aborts a batch; one-class-per-file in src/visualization/; and a "build() returns a Figure, save()/to_html() are optional extras" pattern for chart classes. New code in every phase below should follow these same conventions unless a phase explicitly says otherwise.

Each day below assumes a normal working day (4-6 focused hours). "Definition of Done" is what must be true before moving to the next day -- treat it as a checklist, not a suggestion. When a day's DoD can't be met, stop and fix it before continuing; later days assume earlier ones actually work.

File paths are given relative to the project root (e.g. src/models/signal.py). "Create" means the file does not exist yet. "Modify" means edit an existing file.

## Phase 0 -- Current State (reference, not new work)

Before starting Phase 1, make sure you can explain -- out loud, to someone else -- how a single call to AnalysisService.analyze() flows through the system. If you can't yet, spend half a day tracing it before writing new code:

AnalysisRequest (src/models/analysis_request.py) is built by the Streamlit page from user input (tickers, date range, active indicators, flags for fundamentals/statements/ backtest). AnalysisService.analyze() validates it, resolves the date range and warmup window, then loops over tickers with per-ticker try/except isolation. For each ticker it calls, in order: DataService (fetch + clean OHLCV), IndicatorService (append indicator columns), SignalService (detect Buy/Sell signals from those columns), StatisticsService (period high/low), optionally FundamentalsService and FinancialsService, and optionally BacktestService (which delegates trade execution to BacktestEngine). Everything is assembled into one AnalysisResult per ticker and returned as a list. TechnicalChart consumes a single AnalysisResult and renders a Plotly figure; ExcelExporter and PDFExporter each consume the same AnalysisResult list to produce downloadable files.

Every phase below adds new services that plug into this same loop, and new fields onto AnalysisResult that flow, unchanged in shape, into the chart and exporters. If a phase description ever conflicts with this flow, the flow wins -- don't invent a second data path.

---

## Phase 1 -- Market Structure Engine

_Week 1_

**Goal:** Give every AnalysisResult typed support/resistance levels, a trend classification, and breakout events -- rendered automatically on the chart, not just computed and thrown away.

### Files to Create

| File                                         | Description                                                                                                                                                                                                                                                                                                                                                 |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/models/market_structure.py`             | SupportResistanceLevel (price, level_type: 'support'\|'resistance', strength: int touch count, first_touch/last_touch: date). TrendState enum (BULLISH, BEARISH, SIDEWAYS). TrendClassification (trend: TrendState, strength: float 0-100, since: date). BreakoutEvent (date: datetime, level: float, direction: 'breakout'\|'breakdown', level_type: str). |
| `src/services/support_resistance_service.py` | SupportResistanceService.serve_levels(data, window=20, num_levels=3) -> tuple[list[SupportResistanceLevel], list[SupportResistanceLevel]]. Replaces SignalService.detect_support_resistance's raw float-list return with typed, clustered levels that also count touches.                                                                                   |
| `src/services/trend_service.py`              | TrendService.classify(data) -> TrendClassification. Uses EMA50 vs EMA200 relationship plus recent swing-high/swing-low structure to produce a 0-100 strength score, not just a label.                                                                                                                                                                       |

### Files to Modify

| File                                   | Description                                                                                                                                                                                                                                                                                               |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/models/analysis_result.py`        | Add: support_levels: list[SupportResistanceLevel] = []; resistance_levels: list[SupportResistanceLevel] = []; trend: TrendClassification \| None = None; breakout_events: list[BreakoutEvent] = []. All default to empty/None so existing callers that construct AnalysisResult without these still work. |
| `src/services/analysis_service.py`     | Instantiate SupportResistanceService and TrendService in **init**. In \_analyze_ticker, after visible_indicators is computed, call both services and pass their output into the AnalysisResult constructor.                                                                                               |
| `src/visualization/technical_chart.py` | \_add_support_resistance currently takes list[float]. Change it to take list[SupportResistanceLevel], varying line opacity/width by level.strength (more touches = more visible line). Add \_add_breakout_markers(fig, row, events) using a 'star' marker symbol, same pattern as \_add_signal_trace.     |

### Day-by-Day Plan

#### Day 1 -- Models

Write market_structure.py exactly as specced above. Write a 10-line throwaway script that constructs one of each model with fake data and prints it, to confirm Pydantic validation passes before any real logic exists.

> **Definition of Done:** All four models import and construct without error.

#### Day 2 -- Support/resistance clustering

Implement SupportResistanceService. Start from the existing rolling-extrema logic in SignalService.detect_support_resistance (rolling High/Low max/min over a window), but instead of returning raw floats: (1) collect all extrema candidates, (2) cluster any two within ~1.5% of each other into one level, (3) count how many candidates fell into each cluster as 'strength', (4) keep only the top num_levels per side by strength.

> **Definition of Done:** Given 1 year of daily AAPL data, serve_levels returns 3-5 support and 3-5 resistance levels that visibly line up with chart extrema when you eyeball a plot of Close with hlines at each level.

#### Day 3 -- Trend classification + breakout detection

Implement TrendService.classify: BULLISH if EMA50 > EMA200 and both sloping up over the last ~10 bars, BEARISH for the mirror case, SIDEWAYS otherwise. Strength score: normalize the % gap between EMA50/EMA200 plus the slope magnitude into 0-100. Decide and document what happens when EMA50/EMA200 aren't in the active indicator list (return SIDEWAYS with strength 0 and a note, don't raise). Add breakout detection as a method on SupportResistanceService: a BreakoutEvent fires when Close moves more than ~1% beyond a level after several prior closes stayed within that level's band.

> **Definition of Done:** classify() never raises on missing EMA columns. Breakout events only fire on genuine level crosses, not on every level touch.

#### Day 4 -- Wire into AnalysisService

Add the two new services to AnalysisService.**init**. Call them inside \_analyze_ticker right after visible_indicators is computed. Update analysis_result.py with the new fields (see Modified Files). Run the full pipeline against 2-3 real tickers end-to-end and print the new fields to confirm they're populated and sane.

> **Definition of Done:** AnalysisService.analyze() runs against real tickers with zero new exceptions, and every returned AnalysisResult has non-empty support_levels/resistance_levels/trend for tickers with enough history.

#### Day 5 -- Chart integration

Update TechnicalChart per the Modified Files entry above. Add a small trend badge to the Streamlit page (e.g. st.metric('Trend', 'Bullish', f'{strength:.0f}/100')) near the top of each ticker's tab in stock_analysis.py.

> **Definition of Done:** Opening the Stock Analysis page for a real ticker shows support/resistance lines whose thickness visibly differs by strength, plus a trend badge that updates when you switch tickers.

### How This Connects

AnalysisResult is still the single output contract -- nothing outside of analysis_service.py and technical_chart.py should need to change. ExcelExporter/PDFExporter don't need updates this phase (they're free to add a Market Structure section later, but it's not required for Phase 1 to be 'done').

### Testing Checklist

- [ ] Run analyze() against a ticker with a clear recent uptrend and one with a clear downtrend; confirm TrendState matches what you'd say by eye.
- [ ] Run against a ticker with less than 200 bars of history (shorter period) and confirm EMA200-dependent logic degrades gracefully instead of raising.
- [ ] Force a breakout by picking a ticker that recently broke a visible multi-month range; confirm at least one BreakoutEvent fires near that date.

---

## Phase 2 -- Advanced Technical Analysis

_Week 2_

**Goal:** Every signal gets a confidence score and market context: what regime the market is in, how the ticker is doing versus SPY/its sector, and whether volume confirms the move.

### Files to Create

| File                                        | Description                                                                                                                                                                                                                                                              |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/models/market_regime.py`               | MarketRegime enum (TRENDING, RANGING, VOLATILE) plus a RegimeClassification model (regime: MarketRegime, confidence: float).                                                                                                                                             |
| `src/services/market_regime_service.py`     | MarketRegimeService.classify(data) -> RegimeClassification. Combine ATR-as-%-of-price (volatility) with a simple ADX-style directional measure (or rolling linear-regression slope of Close) to separate trending vs. ranging vs. volatile-chop conditions.              |
| `src/models/relative_strength.py`           | RelativeStrength (ticker_return_pct, benchmark_return_pct, relative_pct, outperforming: bool, benchmark_ticker: str).                                                                                                                                                    |
| `src/services/relative_strength_service.py` | RelativeStrengthService.serve_relative_strength(ticker_data, benchmark_data) -> RelativeStrength, comparing period returns. IMPORTANT: fetch the benchmark (e.g. 'SPY') data ONCE per analyze() call, not once per ticker -- see Wiring notes below.                     |
| `src/models/volume_profile.py`              | VolumeProfile (price_bins: list[float], volume_at_price: list[float], point_of_control: float, value_area_high: float, value_area_low: float).                                                                                                                           |
| `src/services/volume_profile_service.py`    | VolumeProfileService.serve_profile(data, num_bins=20) -> VolumeProfile. Bin closes by price, sum volume per bin, find the point of control (bin with max volume) and the value area (narrowest price range containing ~70% of total volume).                             |
| `src/models/scored_signal.py`               | ScoredSignal (signal: Signal, confidence: float 0-100, contributing_factors: list[str]). A wrapper, not a replacement for Signal -- BacktestEngine and everything else that consumes list[Signal] keeps working unchanged.                                               |
| `src/services/signal_scoring_service.py`    | SignalScoringService.score(signal, result: AnalysisResult) -> ScoredSignal. Confidence goes up when multiple things agree: trend direction matches the signal direction, regime is TRENDING (not VOLATILE), and volume near the signal date is above its recent average. |

### Files to Modify

| File                               | Description                                                                                                                                                                                                                          |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/models/analysis_result.py`    | Add: regime: RegimeClassification \| None = None; relative_strength: RelativeStrength \| None = None; volume_profile: VolumeProfile \| None = None; scored_signals: list[ScoredSignal] = [].                                         |
| `src/services/analysis_service.py` | Fetch the benchmark ticker's data once at the top of analyze() (outside the per-ticker loop), then pass it into RelativeStrengthService for every ticker. Instantiate and call the other three new services inside \_analyze_ticker. |

### Day-by-Day Plan

#### Day 1 -- Regime model + service

Write market_regime.py and market_regime_service.py. Volatility proxy: ATR / Close, expressed as %. Direction proxy: fit a simple linear trend to the last ~20 closes and look at the R^2 (high R^2 + steep slope = TRENDING; low R^2 = RANGING; high ATR% regardless of slope = VOLATILE).

> **Definition of Done:** classify() returns a sensible label for 3 manually-chosen tickers you already know the character of (one clearly trending, one clearly choppy).

#### Day 2 -- Relative strength (with the caching gotcha)

Write relative_strength.py and relative_strength_service.py. In analysis_service.py, fetch SPY data ONCE before the ticker loop starts and reuse it for every ticker in the batch -- fetching it inside the loop means N tickers = N redundant network calls for the exact same data. This is the single most important detail in this phase; get it wrong and analyzing 10 tickers makes 10x more requests than necessary.

> **Definition of Done:** Analyzing a 5-ticker batch results in exactly one extra network call for the benchmark, not five. Verify by temporarily logging every DataService.serve_stock_data call with its ticker argument.

#### Day 3 -- Volume profile

Write volume_profile.py and volume_profile_service.py. Bin the period's Close prices into num_bins evenly-spaced buckets, sum Volume per bucket, point_of_control = bucket with the highest volume. For value_area_high/low: sort bins by volume descending, accumulate until you hit ~70% of total volume, then take the min/max price of the bins included.

> **Definition of Done:** point_of_control lands near a price level that visibly saw a lot of trading on the chart -- sanity check by eye against the candlestick chart.

#### Day 4 -- Signal scoring

Write scored_signal.py and signal_scoring_service.py. For each Signal already in result.signals, compute confidence as a weighted combination: +40 if trend direction agrees with signal direction (BUY needs BULLISH, SELL needs BEARISH), +30 if regime is TRENDING, +30 if volume on the signal's date is above the trailing 20-day average volume. This depends on Phase 1's TrendClassification and this phase's RegimeClassification both being available -- if either is None, skip that component instead of raising.

> **Definition of Done:** Every signal in result.signals has a corresponding ScoredSignal with a confidence between 0 and 100 (never negative, never over 100 -- clamp it).

#### Day 5 -- Wire into AnalysisService + smoke test

Add all four new fields to AnalysisResult, wire the calls into \_analyze_ticker (and the one-time benchmark fetch at the top of analyze()). Run the full pipeline against a 5-ticker batch.

> **Definition of Done:** Full batch runs with one benchmark fetch total, every result has populated regime/relative_strength/volume_profile fields, and scored_signals has the same length as signals.

### How This Connects

The benchmark-fetch-once pattern from Day 2 is the key new wiring concept this phase -- it's the first time analyze() needs to do work outside the per-ticker loop. Everything else follows Phase 1's pattern: new typed fields on AnalysisResult, populated inside \_analyze_ticker, consumed later by whatever page/export code wants them. Volume profile chart rendering (a horizontal histogram overlaid on the price panel) is a reasonable UI addition but isn't required for this phase to be considered done -- treat it as an optional Day 6 if time allows.

### Testing Checklist

- [ ] Confirm total network calls for a batch of N tickers is N+1 (N stock fetches + 1 benchmark fetch), not 2N.
- [ ] Pick a signal you already know was a good call in hindsight and confirm its ScoredSignal confidence is meaningfully higher than a signal that occurred during choppy, low-volume conditions.
- [ ] Confirm scored_signals gracefully returns low/neutral confidence (not a crash) when trend or regime data is missing.

---

## Phase 3 -- Risk Management Suite

_Week 3_

**Goal:** Turn raw indicators into an actionable trade plan: how many shares to buy, where to place a stop, what the risk/reward ratio is.

### Files to Create

| File                                      | Description                                                                                                                                                                                                                                                                                                             |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/models/risk_profile.py`              | PositionSizeRecommendation (shares: int, dollar_amount: float, risk_amount: float, risk_pct: float). StopLossRecommendation (stop_price: float, method: str, take_profit_price: float, risk_reward_ratio: float). TradePlan (entry_price, stop, target, position_size: PositionSizeRecommendation, risk_reward: float). |
| `src/services/risk_service.py`            | RiskService.calculate_risk_reward(entry, stop, target) -> float. Pure calculation, no I/O -- (target - entry) / (entry - stop) for a long position.                                                                                                                                                                     |
| `src/services/position_sizing_service.py` | PositionSizingService.serve_position_size(account_size, risk_pct, entry_price, stop_price) -> PositionSizeRecommendation. Classic formula: risk_amount = account_size \* risk_pct; shares = floor(risk_amount / abs(entry_price - stop_price)).                                                                         |
| `src/services/trade_plan_service.py`      | TradePlanService.build_plan(result: AnalysisResult, account_size, risk_pct) -> TradePlan. Default stop: entry - 2\*ATR if ATR is in result.indicators; fall back to a flat 5% stop if ATR isn't available, and say so in the method's docstring so it's not a silent surprise.                                          |
| `src/services/correlation_service.py`     | CorrelationService.serve_correlation_matrix(price_data: dict[str, pd.DataFrame]) -> pd.DataFrame. Pearson correlation of daily % returns across every ticker's Close column. Used on the Comparison page (Phase 7), not inside analyze().                                                                               |

### Files to Modify

| File                          | Description                                                                                                                                                                                                       |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/components/`             | Create risk_panel.py (new component): a small form for account_size and risk_pct, plus a rendered TradePlan (entry/stop/target/shares/risk-reward) using st.metric, following the same style as metrics_cards.py. |
| `src/pages/stock_analysis.py` | Add an optional 'Trade Plan' expander per ticker tab that calls TradePlanService.build_plan with the sidebar's account_size/risk_pct inputs and renders it via risk_panel.py.                                     |

### Day-by-Day Plan

#### Day 1 -- Models

Write risk_profile.py. Decide up front: is risk_pct a fraction (0.01) or a whole percent (1.0)? Pick one and use it consistently everywhere in this phase -- mixing them is the single most common bug in position-sizing code.

> **Definition of Done:** Models import cleanly; you can state, from memory, whether risk_pct is a fraction or a percent.

#### Day 2 -- Risk/reward + position sizing

Implement risk_service.py and position_sizing_service.py. Write 3 hand-computed examples on paper first (e.g. $10,000 account, 1% risk, $100 entry, $95 stop) and confirm the code produces the exact numbers you computed by hand.

> **Definition of Done:** All 3 hand-computed examples match exactly, including rounding of shares down to a whole number.

#### Day 3 -- Trade plan service

Implement trade_plan_service.py. Handle the ATR-missing case explicitly (this will come up constantly, since ATR is opt-in per AnalysisRequest.indicators). Take profit: a configurable risk/reward multiple of the stop distance (default 2:1) unless you have a better idea from Phase 1's resistance levels (using the nearest resistance level above entry as the target is a nice touch if Phase 1 is done).

> **Definition of Done:** build_plan() never raises when ATR is missing; it falls back and the TradePlan.stop.method field says which method was used.

#### Day 4 -- Correlation service + comparison hook

Implement correlation_service.py. This is a page-level feature, not part of analyze() -- it needs multiple tickers' raw_data at once, which the Comparison page already assembles for its existing chart.

> **Definition of Done:** Given 3+ tickers' price data, serve_correlation_matrix returns a symmetric DataFrame with 1.0 on the diagonal.

#### Day 5 -- UI wiring

Build risk_panel.py and wire it into stock_analysis.py per the Modified Files entry. Add a correlation heatmap to comparison.py using the new service (a simple plotly imshow-style heatmap is fine).

> **Definition of Done:** You can enter an account size and risk %, see a full trade plan for a real ticker, and see a correlation heatmap for a 3-ticker comparison, all without touching AnalysisService.

### How This Connects

This is the first phase where a feature deliberately does NOT live inside AnalysisResult. Risk sizing needs user-supplied inputs (account size, risk tolerance) that have nothing to do with market data -- baking them into the core analyze() pipeline would mean re-running the whole analysis every time someone tweaks their risk %, which is wasteful and architecturally wrong. Keep TradePlanService called directly from the page layer, with AnalysisResult passed in as an argument, not as a field the result carries.

### Testing Checklist

- [ ] Verify the 3 hand-computed position-sizing examples from Day 2 still match after wiring everything together end to end.
- [ ] Confirm build_plan() doesn't crash for a ticker analyzed without the atr indicator active.
- [ ] Confirm the correlation matrix is symmetric and has 1.0 on the diagonal for every ticker.

---

## Phase 4 -- Backtesting Engine v2

_Week 4_

**Goal:** Add the metrics a real trader expects from a backtest -- Sortino, profit factor, expectancy, per-trade attribution -- without breaking BacktestResult, which PDFExporter and ExcelExporter already depend on.

### Files to Create

| File                                       | Description                                                                                                                                                                                                                                     |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/models/backtest_metrics.py`           | ExtendedBacktestMetrics (sortino_ratio: float, profit_factor: float, expectancy: float, avg_winner: float, avg_loser: float, largest_winner: float, largest_loser: float). A separate model, NOT new fields bolted onto BacktestResult.         |
| `src/services/backtest_metrics_service.py` | BacktestMetricsService.calculate(backtest: BacktestResult) -> ExtendedBacktestMetrics, computed entirely from backtest.trades and backtest.equity_curve -- it never touches raw price data, only what's already in the existing BacktestResult. |
| `src/visualization/equity_curve_chart.py`  | EquityCurveChart class, same shape as ComparisonChart (build()/save()/to_html(), uses ChartTheme). Plots the portfolio value line plus a shaded drawdown-from-peak area beneath it.                                                             |

### Files to Modify

| File                               | Description                                                                                                                                                                                                                                                                                                                 |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/components/backtest_panel.py` | Currently renders only total_return/sharpe_ratio/max_drawdown/win_rate. Extend to also accept an optional ExtendedBacktestMetrics and render a second row of metrics when it's provided -- keep the function backward compatible when it's not (default None, same pattern as metrics_cards.py's optional deltas argument). |

### Day-by-Day Plan

#### Day 1 -- Formulas

Implement backtest*metrics.py and the calculation methods. Sortino: like Sharpe but only penalizes downside volatility (std of negative daily returns only). Profit factor: gross profit / gross loss (absolute value) across all trades. Expectancy: (win_rate * avg*winner) - (loss_rate * avg_loser). Write these against a tiny hand-built list of 5-6 fake Trade objects with known P&L so you can verify each number by hand.

> **Definition of Done:** All formulas match hand-calculated values on the fake trade set, including the edge case of zero losing trades (profit factor should not divide by zero).

#### Day 2 -- Equity curve chart

Build equity_curve_chart.py. Drawdown shading: compute running max of the Portfolio column, shade the area between Portfolio and its running max wherever Portfolio is below it.

> **Definition of Done:** Chart visibly shows the equity line and shaded drawdown periods for a real backtest run.

#### Day 3 -- Trade attribution

Add a method to BacktestMetricsService (or a small helper) that ranks backtest.trades by pnl descending/ascending to surface the single biggest winner and biggest loser, plus which entry conditions (from Signal.reason, if you kept that association) tended to produce winners vs. losers.

> **Definition of Done:** You can answer 'what was this backtest's best and worst trade, and by how much' from the output alone.

#### Day 4 -- Wire into UI

Update backtest_panel.py per the Modified Files entry. Call BacktestMetricsService and EquityCurveChart from wherever backtesting results are already rendered (stock_analysis.py today, or the dedicated backtesting.py page once Phase 7 exists).

> **Definition of Done:** Running a backtest in the app shows the original 4 metrics plus the new extended metrics and the equity curve chart, with no change needed to BacktestResult itself.

#### Day 5 -- Full smoke test

Run a backtest end to end on 2-3 tickers with different characteristics (one with many trades, one with very few) and confirm nothing divides by zero or crashes on edge cases (zero trades, all-winning trades, all-losing trades).

> **Definition of Done:** Zero-trade and single-trade backtests don't crash; they render sensible defaults (e.g. 'N/A' or 0) instead.

### How This Connects

The core lesson of this phase: when you need more derived data from an existing model, don't widen that model and risk breaking every existing consumer (PDFExporter, ExcelExporter, backtest_panel.py all already depend on BacktestResult's exact shape). Instead, write a service that takes the existing model as input and returns a new, separate model. Same principle you'll want to remember for every future phase that's tempted to bolt fields onto an already-depended-upon model.

### Testing Checklist

- [ ] Hand-verify Sortino, profit factor, and expectancy against a small fake trade list before trusting them on real data.
- [ ] Run against a backtest with zero completed trades and confirm no ZeroDivisionError anywhere in the new service.
- [ ] Confirm existing PDF/Excel exports still work unchanged -- this phase should require zero modifications to either exporter.

---

## Phase 5 -- Fundamental Intelligence

_Week 5_

**Goal:** Round out the fundamentals picture: earnings calendar, analyst sentiment, insider activity, and sector context -- reusing what already exists wherever possible.

### Files to Create

| File                                | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/models/earnings.py`            | EarningsEvent (date: date, is_estimate: bool, eps_estimate: float \| None, eps_actual: float \| None).                                                                                                                                                                                                                                                                                                                                                                            |
| `src/services/earnings_service.py`  | EarningsService.serve_earnings(ticker) -> list[EarningsEvent]. FundamentalsService.serve_earnings_dates already exists and fetches this raw data (via yf.Ticker(ticker).calendar) -- this service should call that existing method and convert its output into typed EarningsEvent models, not re-implement the yfinance call from scratch.                                                                                                                                       |
| `src/models/analyst_rating.py`      | AnalystRating (consensus: str, num_analysts: int, price_target_mean: float \| None, price_target_high: float \| None, price_target_low: float \| None).                                                                                                                                                                                                                                                                                                                           |
| `src/services/analyst_service.py`   | AnalystService.serve_ratings(ticker) -> AnalystRating \| None, via yf.Ticker(ticker).recommendations and .analyst_price_targets. Wrap in try/except returning None on failure, matching FundamentalsService's existing pattern.                                                                                                                                                                                                                                                   |
| `src/models/insider_transaction.py` | InsiderTransaction (insider_name: str, date: date, transaction_type: str, shares: int, value: float \| None).                                                                                                                                                                                                                                                                                                                                                                     |
| `src/services/insider_service.py`   | InsiderService.serve_transactions(ticker) -> list[InsiderTransaction], via yf.Ticker(ticker).insider_transactions.                                                                                                                                                                                                                                                                                                                                                                |
| `src/models/sector_benchmark.py`    | SectorBenchmark (sector: str, avg_pe: float \| None, ticker_pe: float \| None, pe_percentile: float \| None). KNOWN LIMITATION: yfinance has no built-in sector-average endpoint, so this needs either a small static reference table you maintain yourself, or comparing against a handful of manually-chosen peer tickers in the same sector. Document this limitation in the module docstring rather than quietly shipping something that looks more authoritative than it is. |
| `src/services/benchmark_service.py` | BenchmarkService.serve_sector_benchmark(ticker, fundamentals: Fundamentals) -> SectorBenchmark \| None. See the limitation noted above.                                                                                                                                                                                                                                                                                                                                           |

### Files to Modify

| File                                   | Description                                                                                                                                                                                                                       |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/models/analysis_request.py`       | Add include_earnings, include_analyst_ratings, include_insider_activity: bool = False, matching the existing include_fundamentals/include_statements pattern.                                                                     |
| `src/models/analysis_result.py`        | Add: earnings: list[EarningsEvent] = []; analyst_rating: AnalystRating \| None = None; insider_transactions: list[InsiderTransaction] = []; sector_benchmark: SectorBenchmark \| None = None.                                     |
| `src/components/fundamentals_panel.py` | Extend to optionally render the new sections when present, following the existing 'skip if None/empty' pattern already used throughout the codebase (see ExcelExporter's _write_\*\_sheet methods for the exact pattern to copy). |

### Day-by-Day Plan

#### Day 1 -- Earnings (reuse, don't duplicate)

Write earnings.py and earnings_service.py. Read FundamentalsService.serve_earnings_dates first -- it already fetches the raw calendar data. Your new service's job is only to call it and reshape the output into EarningsEvent models.

> **Definition of Done:** serve_earnings returns typed models for a ticker with an upcoming earnings date, and an empty list (not a crash) for one without calendar data available.

#### Day 2 -- Analyst ratings

Write analyst_rating.py and analyst_service.py. Expect this yfinance data to be inconsistently available across tickers -- test against at least 3 different tickers, including a smaller/less-covered one, to see the None case in practice, not just in theory.

> **Definition of Done:** serve_ratings returns None gracefully (never raises) for a ticker with no analyst coverage.

#### Day 3 -- Insider transactions

Write insider_transaction.py and insider_service.py.

> **Definition of Done:** serve_transactions returns a list (possibly empty) for any valid ticker without raising.

#### Day 4 -- Sector benchmark (with documented limitation)

Write sector_benchmark.py and benchmark_service.py per the limitation noted above. Simplest honest version: compare the ticker's P/E against 2-3 manually chosen peers you fetch Fundamentals for on the fly (e.g. for a tech ticker, compare against a couple of well-known peers), rather than pretending to have a real sector database.

> **Definition of Done:** The module docstring clearly states this is a peer-comparison approximation, not a true sector database, so nobody mistakes it for more than it is.

#### Day 5 -- Wire into request/result/page

Update analysis*request.py, analysis_result.py, and analysis_service.py to call the new services when their respective include*\* flag is set. Update fundamentals_panel.py to render the new sections.

> **Definition of Done:** Toggling each new include\_\* flag in the sidebar shows the corresponding new section in the Fundamentals panel, and leaving all of them off changes nothing about existing behavior.

### How This Connects

This phase is the most yfinance-data-availability-dependent one so far -- expect None/empty results far more often than in earlier phases, and design every panel section to skip cleanly when data isn't there, exactly like FundamentalsService already does for the fundamentals it can't fetch.

### Testing Checklist

- [ ] Test each new service against at least 3 tickers of varying size/coverage (e.g. a mega-cap, a mid-cap, a smaller one) to see realistic None/empty behavior, not just the happy path.
- [ ] Confirm turning off all four include\_\* flags leaves AnalysisResult and the rendered page identical to before this phase existed.

---

## Phase 6 -- Portfolio Analytics

_Week 6_

**Goal:** Let a user record actual holdings (not just a watchlist of tickers) and see allocation, diversification, and benchmark-relative performance across their whole portfolio.

### Files to Create

| File                                | Description                                                                                                                                                                                                                                                                                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/models/holding.py`             | Holding (ticker: str, shares: float, cost_basis: float, purchase_date: date).                                                                                                                                                                                                                                                                     |
| `src/models/portfolio.py`           | Portfolio (name: str, holdings: list[Holding]).                                                                                                                                                                                                                                                                                                   |
| `src/models/portfolio_analysis.py`  | PortfolioAnalysis (total_value: float, total_cost: float, total_return_pct: float, allocation: dict[str, float] ticker->pct, sector_allocation: dict[str, float] sector->pct, diversification_score: float, benchmark_return_pct: float \| None).                                                                                                 |
| `src/services/portfolio_service.py` | PortfolioService.serve_analysis(portfolio: Portfolio, price_data: dict[str, pd.DataFrame], fundamentals: dict[str, Fundamentals]) -> PortfolioAnalysis. Diversification score: something as simple as 1 - Herfindahl index of allocation weights is a reasonable, explainable starting point -- don't over-engineer this into a research project. |
| `src/utils/portfolio_storage.py`    | load_portfolios() / save_portfolios(), same JSON-file-in-cache/ pattern as stock_analysis.py's \_load_cached_tickers/\_save_cached_tickers. Reuse that exact pattern rather than inventing a new persistence approach.                                                                                                                            |

### Files to Modify

| File         | Description                                                                                                                                |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `src/pages/` | Create src/pages/portfolio.py (new page, do not repurpose watchlists.py -- see the Wiring note below on why these are different concepts). |

### Day-by-Day Plan

#### Day 1 -- Models + persistence

Write holding.py, portfolio.py, and portfolio_storage.py. Copy stock_analysis.py's JSON caching pattern directly -- same Path-based cache file approach, same read-json-or-return-empty-on-failure shape.

> **Definition of Done:** You can save a Portfolio to disk and load it back with all fields intact across a script restart.

#### Day 2 -- Allocation + diversification

Write portfolio_analysis.py and the core of portfolio_service.py: total_value/total_cost/total_return_pct from holdings + current prices, allocation as each holding's value / total_value, diversification_score via the Herfindahl-index approach noted above.

> **Definition of Done:** A 3-holding portfolio with roughly equal position sizes scores meaningfully higher on diversification than the same portfolio with one dominant 90% position.

#### Day 3 -- Sector allocation viz

Add sector_allocation to portfolio_service.py using each holding's Fundamentals.sector. Render as a pie or donut chart via Plotly, following ChartTheme for color consistency with the rest of the app.

> **Definition of Done:** The sector chart's slice percentages sum to 100% and visually match the allocation dict's values.

#### Day 4 -- Benchmark comparison

Wire in Phase 2's RelativeStrengthService to compare the portfolio's blended return against SPY over the same period. This is a direct reuse of existing Phase 2 work, not new calculation logic -- if you're writing new benchmark-comparison math here, you've duplicated Phase 2 and should stop and reuse instead.

> **Definition of Done:** benchmark_return_pct is populated by calling into RelativeStrengthService, not a second independent implementation.

#### Day 5 -- Portfolio page

Build src/pages/portfolio.py: a form to add/edit/remove holdings (ticker, shares, cost basis, purchase date), a call to portfolio_service.serve_analysis, and rendering of the results (metrics cards + sector pie chart).

> **Definition of Done:** You can add 3 real holdings through the UI, see the portfolio's total return and sector breakdown, and have it persist after closing and reopening the app.

### How This Connects

Watchlists and portfolios are different concepts, even though the roadmap document mentions both under similar headings: a watchlist is just a list of tickers you're watching (no shares, no cost basis, no P&L) -- that's what watchlists.py should eventually become. A portfolio is actual holdings with real P&L. Keep them as separate pages backed by separate models; don't merge them just because they both involve 'a list of tickers'.

### Testing Checklist

- [ ] Add a holding, close and reopen the app, and confirm it's still there (persistence actually works, not just in-session state).
- [ ] Confirm allocation percentages across all holdings sum to (approximately) 100%.
- [ ] Confirm a single-holding portfolio doesn't crash diversification scoring (edge case: Herfindahl index of one 100% position).

---

## Phase 7 -- Streamlit Trading Terminal

_Week 7_

**Goal:** Turn the collection of stub pages into an actual multi-page application by wiring every previously-stubbed page to the real services built in Phases 1-6.

### Files to Modify

| File                       | Description                                                                                                                                                                                                                                                                                                                 |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/pages/dashboard.py`   | Currently a stub. Build into a summary view across the user's watchlist: for each ticker, run a lightweight analyze() (short period, minimal indicators) and show trend state, regime, and the most recent scored signal in a compact table/card grid -- not a full chart per ticker, this page is a scan, not a deep-dive. |
| `src/pages/comparison.py`  | Currently a stub. Build using the existing ComparisonService (already returns a go.Figure) plus Phase 2's RelativeStrengthService per ticker and Phase 3's CorrelationService across the selected tickers as a heatmap.                                                                                                     |
| `src/pages/backtesting.py` | Currently a stub. Build into a dedicated page (rather than an inline section of stock_analysis.py): ticker + strategy inputs, a call to BacktestService, rendering via backtest_panel.py plus Phase 4's EquityCurveChart.                                                                                                   |
| `src/pages/settings.py`    | Currently a stub. Build into a preferences page: default active indicators, default account_size/risk_pct for Phase 3's position sizing, persisted via the same JSON-in-cache/ pattern used elsewhere.                                                                                                                      |
| `src/pages/watchlists.py`  | Currently a stub. Build into a simple ticker-list manager (add/remove tickers, no shares/cost-basis -- see Phase 6's Wiring note on why this is deliberately separate from Portfolio).                                                                                                                                      |
| `main.py / app shell`      | Whatever currently routes between pages (a sidebar radio, st.navigation, or similar) needs every page above reachable and needs to confirm session_state keys don't collide between pages -- e.g. two pages both using 'selected_tickers' as a key will fight each other unless that's intentional shared state.            |

### Day-by-Day Plan

#### Day 1 -- Dashboard

Build dashboard.py as a lightweight multi-ticker scan (see Modified Files). Keep each ticker's mini-analysis fast -- don't fetch fundamentals/statements/backtest here, just price + a couple of indicators + trend/regime.

> **Definition of Done:** Opening the dashboard with a 5-ticker watchlist loads noticeably faster than opening Stock Analysis for all 5 individually.

#### Day 2 -- Comparison page

Build comparison.py per Modified Files: ComparisonChart for normalized price, a small table of each ticker's RelativeStrength vs. SPY, and a correlation heatmap.

> **Definition of Done:** Selecting 3-4 tickers shows all three views without error, and the correlation heatmap's diagonal is visibly 1.0.

#### Day 3 -- Backtesting page

Build backtesting.py as its own page, moving backtest configuration out of stock_analysis.py's inline flow if it's currently there. Reuse BacktestService and Phase 4's EquityCurveChart/ExtendedBacktestMetrics directly -- this page shouldn't contain any new backtest math of its own.

> **Definition of Done:** Running a backtest from this dedicated page produces identical numbers to running the same backtest from wherever it lived before -- if the numbers differ, something got duplicated instead of reused.

#### Day 4 -- Settings + navigation wiring

Build settings.py per Modified Files. Audit every page's st.session_state key usage and resolve collisions -- write down every key each page reads/writes before touching navigation code, so conflicts are visible on paper before they're invisible bugs in the app.

> **Definition of Done:** You have a written list of every session_state key used across all pages, and no two unrelated pages silently share a key.

#### Day 5 -- End-to-end walkthrough

Click through every single page in order, doing a realistic task on each one (add a ticker, run an analysis, compare two tickers, run a backtest, adjust a setting, check the dashboard reflects it). Fix whatever breaks.

> **Definition of Done:** A full click-through of all 6 pages completes with zero unhandled exceptions and no page showing stale data left over from another page.

### How This Connects

This week is explicitly about NOT writing new calculation logic -- every page here should be gluing together services that already exist from Phases 1-6. If you find yourself writing a new formula in a page file, stop; that logic belongs in a service, and the page should just call it.

### Testing Checklist

- [ ] Full click-through of all 6 pages in one sitting, doing a realistic task on each.
- [ ] Confirm no two pages silently clobber each other's session_state.
- [ ] Confirm the Dashboard page loads meaningfully faster than opening every watchlist ticker individually in Stock Analysis.

---

## Phase 8 -- Alerts and Automation

_Week 8_

**Goal:** Detect when something worth noticing happens (a signal, a breakout, a threshold) and notify the user -- including confronting the real architectural question of what 'scheduled' means inside a Streamlit app.

### Files to Create

| File                                                                              | Description                                                                                                                                                                                                               |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/models/alert_rule.py`                                                        | AlertRule (ticker: str, condition_type: str e.g. 'price_above'\|'price_below'\|'rsi_above'\|'rsi_below'\|'new_signal', threshold: float \| None). TriggeredAlert (rule: AlertRule, triggered_at: datetime, message: str). |
| `src/services/alert_service.py`                                                   | AlertService.check_conditions(result: AnalysisResult, rules: list[AlertRule]) -> list[TriggeredAlert]. Pure function of an AnalysisResult and a rule list -- no scheduling, no email, just condition matching.            |
| `src/services/notification_service.py`                                            | NotificationService.send_email(to, subject, body) via smtplib. Credentials come from Streamlit secrets (.streamlit/secrets.toml) or environment variables -- NEVER hardcoded or committed to the repo.                    |
| `scripts/run_watchlist_scan.py (or src/services/scheduler_service.py, see Day 3)` | See the architectural fork described in Day 3 before creating either of these -- don't build both a Streamlit-internal scheduler and a standalone script; pick one approach deliberately.                                 |

### Files to Modify

| File                     | Description                                                                                                    |
| ------------------------ | -------------------------------------------------------------------------------------------------------------- |
| `src/pages/settings.py`  | Add an Alerts section: add/remove AlertRule entries, persisted the same JSON-in-cache/ way as everything else. |
| `src/pages/dashboard.py` | Show currently-active TriggeredAlert entries at the top of the page.                                           |

### Day-by-Day Plan

#### Day 1 -- Alert rule model + condition matching

Write alert_rule.py and alert_service.py. Cover at minimum: price crosses above/below a threshold, RSI crosses above/below a threshold, and a new Signal appearing in result.signals since the last check.

> **Definition of Done:** Given a fabricated AnalysisResult where you know a condition should fire, check_conditions returns exactly the TriggeredAlert you expect -- and returns nothing for conditions that shouldn't fire.

#### Day 2 -- Email notification

Write notification_service.py. Set up a real test email account and confirm an actual email arrives -- don't stop at 'the function didn't raise an exception', that tells you almost nothing about whether email delivery actually works.

> **Definition of Done:** A real test email, sent through this service, actually lands in a real inbox.

#### Day 3 -- The scheduling decision (read this before coding)

Streamlit apps only run code while a user has the page open and interacts with it (or via st_autorefresh-style polling) -- there is no built-in background job runner. Decide explicitly between: (a) a separate standalone Python script (scripts/run_watchlist_scan.py) that imports AnalysisService directly and is triggered by an OS-level scheduler (cron on Linux/Mac, Task Scheduler on Windows), or (b) an in-app polling loop using a Streamlit auto-refresh mechanism while the app is open. Option (a) is more reliable and is the recommended default; only choose (b) if the alerts genuinely only matter while someone is actively watching the app.

> **Definition of Done:** You can state, in one sentence, which option you chose and why -- and you haven't built both.

#### Day 4 -- Watchlist scanning

Implement whichever option Day 3 selected: loop AnalysisService.analyze() over every ticker in the user's watchlist, run AlertService.check_conditions against each result, collect every TriggeredAlert, and call NotificationService for any new ones (track which alerts were already sent so you don't re-email the same trigger on every run).

> **Definition of Done:** Running the scan twice in a row against unchanged data sends the notification email only once, not twice.

#### Day 5 -- UI wiring + end-to-end test

Wire the Alerts section into settings.py and the active-alerts display into dashboard.py per Modified Files. Set an artificially easy-to-trigger rule (e.g. 'price_above' set just below the current price) and confirm the whole chain fires: rule saved -> scan runs -> alert triggers -> email arrives -> dashboard shows it.

> **Definition of Done:** The full chain -- from adding a rule in Settings to an email landing in your inbox -- works end to end for at least one manually-forced trigger.

### How This Connects

Day 3 is the most important day in this phase, not the most code. Getting the scheduling architecture wrong (e.g. assuming Streamlit can silently run code in the background while nobody has the app open) will produce something that appears to work in testing and then does nothing useful in real use.

### Testing Checklist

- [ ] Confirm a real email actually arrives, not just that the function call didn't raise.
- [ ] Confirm re-running the same scan twice doesn't send duplicate notifications for the same trigger.
- [ ] If you chose the standalone-script approach, confirm it runs correctly when invoked completely outside of Streamlit (e.g. python scripts/run_watchlist_scan.py from a plain terminal).

---

## Phase 9 -- AI and Quant Layer (Future / Stretch)

_Future_

**Goal:** This phase is explicitly open-ended and substantially harder than Phases 1-8 -- it introduces external LLM/API dependencies, unstructured data (news), and real machine learning with a labeled-data pipeline. Attempt it only after Phases 1-8 are stable and in regular use; treat everything below as milestones to sequence yourself, not a day-by-day plan.

### Files to Create

| File                                            | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/services/market_summary_service.py`        | Calls an LLM API (e.g. the Anthropic API) with a prompt built from an AnalysisResult's statistics, trend, and TrendCommentator output, asking for a short natural-language summary. Straightforward to prototype, but needs an API key managed via secrets, and needs a hard character/token budget so a bad response doesn't overflow the PDF/UI.                                                                                                                                                        |
| `src/services/sentiment_service.py`             | Requires a news API (not yfinance) and a sentiment model or LLM call per headline. This is the first phase requiring a genuinely new external data source, not just more yfinance endpoints -- budget real time for evaluating and signing up for a news API before writing any code against it.                                                                                                                                                                                                          |
| `src/services/strategy_optimization_service.py` | Grid-search over indicator parameters (e.g. RSI period, EMA lengths) by calling BacktestService repeatedly and keeping the best-performing combination. This is the most achievable item in this phase since it's pure reuse of existing BacktestService in a loop -- a reasonable first milestone if you want a foothold in Phase 9 without the external-API complexity of the other items.                                                                                                              |
| `src/services/feature_importance_service.py`    | The heaviest lift in this phase: requires building a labeled dataset (historical indicator readings -> forward N-day return), training a real model (e.g. scikit-learn gradient boosting), and evaluating feature importance properly (with train/test splits, not just fitting on everything and reading .feature*importances*). Do not attempt this before the strategy optimization milestone above is working -- it depends on the same backtesting infrastructure and is considerably more involved. |

### How This Connects

Every item in this phase should be built as an isolated, optional add-on that AnalysisService and AnalysisResult don't need to know about unless a caller explicitly asks for it -- follow the include_fundamentals/include_statements pattern: an opt-in flag, a None default, and total silence in the rest of the app when it's off. An LLM outage or a missing news API key should never be able to break core stock analysis.

### Testing Checklist

- [ ] Confirm the rest of the application works completely normally with no API keys configured for anything in this phase.
- [ ] For strategy optimization specifically: confirm the 'best' parameters found aren't wildly overfit to one narrow date range -- test the winning parameters against a different, later date range before trusting them.

---

## Appendix -- Full New-File Index

Every new file introduced across all phases, in one place for quick reference once you're mid-implementation and just need the list.

| File                                                                              | Phase   |
| --------------------------------------------------------------------------------- | ------- |
| `src/models/market_structure.py`                                                  | Phase 1 |
| `src/services/support_resistance_service.py`                                      | Phase 1 |
| `src/services/trend_service.py`                                                   | Phase 1 |
| `src/models/market_regime.py`                                                     | Phase 2 |
| `src/services/market_regime_service.py`                                           | Phase 2 |
| `src/models/relative_strength.py`                                                 | Phase 2 |
| `src/services/relative_strength_service.py`                                       | Phase 2 |
| `src/models/volume_profile.py`                                                    | Phase 2 |
| `src/services/volume_profile_service.py`                                          | Phase 2 |
| `src/models/scored_signal.py`                                                     | Phase 2 |
| `src/services/signal_scoring_service.py`                                          | Phase 2 |
| `src/models/risk_profile.py`                                                      | Phase 3 |
| `src/services/risk_service.py`                                                    | Phase 3 |
| `src/services/position_sizing_service.py`                                         | Phase 3 |
| `src/services/trade_plan_service.py`                                              | Phase 3 |
| `src/services/correlation_service.py`                                             | Phase 3 |
| `src/models/backtest_metrics.py`                                                  | Phase 4 |
| `src/services/backtest_metrics_service.py`                                        | Phase 4 |
| `src/visualization/equity_curve_chart.py`                                         | Phase 4 |
| `src/models/earnings.py`                                                          | Phase 5 |
| `src/services/earnings_service.py`                                                | Phase 5 |
| `src/models/analyst_rating.py`                                                    | Phase 5 |
| `src/services/analyst_service.py`                                                 | Phase 5 |
| `src/models/insider_transaction.py`                                               | Phase 5 |
| `src/services/insider_service.py`                                                 | Phase 5 |
| `src/models/sector_benchmark.py`                                                  | Phase 5 |
| `src/services/benchmark_service.py`                                               | Phase 5 |
| `src/models/holding.py`                                                           | Phase 6 |
| `src/models/portfolio.py`                                                         | Phase 6 |
| `src/models/portfolio_analysis.py`                                                | Phase 6 |
| `src/services/portfolio_service.py`                                               | Phase 6 |
| `src/utils/portfolio_storage.py`                                                  | Phase 6 |
| `src/models/alert_rule.py`                                                        | Phase 8 |
| `src/services/alert_service.py`                                                   | Phase 8 |
| `src/services/notification_service.py`                                            | Phase 8 |
| `scripts/run_watchlist_scan.py (or src/services/scheduler_service.py, see Day 3)` | Phase 8 |
| `src/services/market_summary_service.py`                                          | Phase 9 |
| `src/services/sentiment_service.py`                                               | Phase 9 |
| `src/services/strategy_optimization_service.py`                                   | Phase 9 |
| `src/services/feature_importance_service.py`                                      | Phase 9 |
