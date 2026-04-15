"""
backtest.py — Signal-driven long-only backtester
=================================================

Strategy:
  - BUY  : invest all available cash at the closing price of a Buy-signal bar.
  - SELL : liquidate the entire position at the closing price of a Sell-signal bar.
  - Any open position at the end of the period is marked to market at the last close.

Metrics returned:
  total_return_pct, buy_hold_return_pct, num_trades, win_rate,
  max_drawdown_pct, sharpe_ratio, portfolio_series, trades
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ── Trade record ──────────────────────────────────────────────────────────────


@dataclass
class Trade:
    kind: str           # "BUY" or "SELL"
    date: pd.Timestamp
    price: float
    shares: float
    value: float
    pnl: Optional[float] = None        # populated on SELL
    pnl_pct: Optional[float] = None    # populated on SELL


# ── Core engine ───────────────────────────────────────────────────────────────


def run_backtest(
    data: pd.DataFrame,
    signals: pd.DataFrame,
    initial_capital: float = 10_000.0,
) -> dict:
    """
    Run a simple long-only backtest driven by the pre-computed signal DataFrame.

    Args:
        data:            OHLCV DataFrame indexed by date (same index as signals).
        signals:         DataFrame with columns ``Buy`` and ``Sell``.
                         Non-NaN entries mark signal bars.
        initial_capital: Starting portfolio cash (default $10,000).

    Returns:
        Dict of performance metrics, the full portfolio value series, and trade log.
        Returns an empty dict if input data is invalid.
    """
    if data is None or data.empty or signals is None or signals.empty:
        log.warning("Backtest skipped — invalid data or signals.")
        return {}

    cash: float = initial_capital
    shares: float = 0.0
    entry_price: Optional[float] = None
    trades: list[Trade] = []
    pv_index: list[pd.Timestamp] = []
    pv_values: list[float] = []

    for date, row in data.iterrows():
        close = row.get("Close")
        if close is None or pd.isna(close) or close <= 0:
            pv_index.append(date)
            pv_values.append(cash + shares * (close or 0))
            continue

        sig = signals.loc[date] if date in signals.index else None

        # ── Enter long position ───────────────────────────────────────────────
        if sig is not None and pd.notna(sig.get("Buy")) and shares == 0 and cash > 0:
            shares = cash / close
            entry_price = close
            cash = 0.0
            trades.append(
                Trade(
                    kind="BUY",
                    date=date,
                    price=close,
                    shares=shares,
                    value=shares * close,
                )
            )
            log.debug(f"BUY  {date.date()} @ {close:.2f} — {shares:.4f} shares")

        # ── Exit long position ────────────────────────────────────────────────
        elif sig is not None and pd.notna(sig.get("Sell")) and shares > 0:
            proceeds = shares * close
            cost_basis = shares * entry_price  # type: ignore[operator]
            pnl = proceeds - cost_basis
            pnl_pct = (pnl / cost_basis) * 100 if cost_basis else 0.0
            trades.append(
                Trade(
                    kind="SELL",
                    date=date,
                    price=close,
                    shares=shares,
                    value=proceeds,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                )
            )
            log.debug(
                f"SELL {date.date()} @ {close:.2f} — "
                f"P&L {pnl_pct:+.2f}%"
            )
            cash = proceeds
            shares = 0.0
            entry_price = None

        # Portfolio snapshot
        pv_index.append(date)
        pv_values.append(cash + shares * close)

    # Mark any open position to market at the final close
    final_close = float(data["Close"].iloc[-1])
    final_value = cash + shares * final_close

    portfolio_series = pd.Series(pv_values, index=pv_index, name="Portfolio")

    # ── Aggregate metrics ─────────────────────────────────────────────────────
    total_return_pct = ((final_value - initial_capital) / initial_capital) * 100

    first_close = float(data["Close"].iloc[0])
    buy_hold_return_pct = (
        ((final_close - first_close) / first_close) * 100 if first_close else 0.0
    )

    sell_trades = [t for t in trades if t.kind == "SELL"]
    num_complete_trades = len(sell_trades)
    win_rate = (
        sum(1 for t in sell_trades if (t.pnl or 0) > 0) / num_complete_trades * 100
        if num_complete_trades > 0
        else 0.0
    )

    # Max drawdown
    rolling_max = portfolio_series.cummax()
    drawdown = (portfolio_series - rolling_max) / rolling_max * 100
    max_drawdown_pct = float(drawdown.min()) if not drawdown.empty else 0.0

    # Annualised Sharpe (risk-free rate ≈ 0)
    daily_ret = portfolio_series.pct_change().dropna()
    sharpe_ratio = (
        float((daily_ret.mean() / daily_ret.std()) * np.sqrt(252))
        if daily_ret.std() > 0
        else 0.0
    )

    # Alpha vs buy & hold
    bh_series = (data["Close"] / data["Close"].iloc[0]) * initial_capital
    alpha_pct = total_return_pct - buy_hold_return_pct

    result = {
        "initial_capital": initial_capital,
        "final_value": final_value,
        "total_return_pct": total_return_pct,
        "buy_hold_return_pct": buy_hold_return_pct,
        "alpha_pct": alpha_pct,
        "num_trades": len(trades),
        "num_complete_trades": num_complete_trades,
        "win_rate": win_rate,
        "max_drawdown_pct": max_drawdown_pct,
        "sharpe_ratio": sharpe_ratio,
        "trades": trades,
        "portfolio_series": portfolio_series,
    }

    log.debug(
        f"Backtest complete — return={total_return_pct:+.1f}%, "
        f"B&H={buy_hold_return_pct:+.1f}%, alpha={alpha_pct:+.1f}%, "
        f"trades={len(trades)}, win={win_rate:.0f}%, "
        f"drawdown={max_drawdown_pct:.1f}%, sharpe={sharpe_ratio:.2f}"
    )

    return result
