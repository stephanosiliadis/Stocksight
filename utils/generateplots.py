import os
import logging
from typing import Any

import matplotlib.pyplot as plt
import mplfinance as mpf
from matplotlib.lines import Line2D
import pandas as pd

log = logging.getLogger(__name__)

# Chart color constants
_GREEN = "#26a69a"
_RED = "#ef5350"
_BLUE = "royalblue"
_ORANGE = "darkorange"
_PURPLE = "mediumpurple"
_CYAN = "deepskyblue"
_LIME = "limegreen"
_GOLD = "goldenrod"
_TOMATO = "tomato"


def generate_plots(
    data: pd.DataFrame,
    ticker: str,
    indicators: list,
    signals_data: pd.DataFrame | None = None,
    support_levels: list | None = None,
    resistance_levels: list | None = None,
    output_dir: str = "data",
) -> str:
    """
    Dynamically build a multi-panel technical analysis chart based on the
    set of active indicators.

    Panel layout (only panels for active indicators are created):
        Panel 0  — RSI / Stochastic oscillator (if either enabled)
        Panel N  — Candlestick (always; overlaid with BB, EMAs, signals, S/R)
        Panel N+1 — Volume (if enabled)
        Panel N+2 — MACD (if enabled)
        Panel N+3 — ATR (if enabled)
    """
    addplots = []
    panel_ratios = []
    current_panel = 0

    # ─── Oscillator panel (RSI / Stochastic) ────────────────────────────────
    has_rsi = "rsi" in indicators and "RSI" in data.columns
    has_stoch = "stochastic" in indicators and "Stoch_K" in data.columns
    oscillator_panel = None

    if has_rsi or has_stoch:
        if has_rsi:
            addplots.append(
                mpf.make_addplot(
                    data["RSI"],
                    panel=current_panel,
                    color=_BLUE,
                    ylabel="RSI",
                    width=1.2,
                )
            )
            # Overlay Stochastic on the same RSI panel when both are active
            if has_stoch:
                addplots.append(
                    mpf.make_addplot(
                        data["Stoch_K"],
                        panel=current_panel,
                        color=_ORANGE,
                        linestyle="--",
                        width=1.0,
                    )
                )
                addplots.append(
                    mpf.make_addplot(
                        data["Stoch_D"],
                        panel=current_panel,
                        color=_TOMATO,
                        linestyle=":",
                        width=1.0,
                    )
                )
        else:
            addplots.append(
                mpf.make_addplot(
                    data["Stoch_K"],
                    panel=current_panel,
                    color=_ORANGE,
                    ylabel="Stoch",
                    width=1.2,
                )
            )
            addplots.append(
                mpf.make_addplot(
                    data["Stoch_D"],
                    panel=current_panel,
                    color=_TOMATO,
                    linestyle="--",
                    width=1.0,
                )
            )

        oscillator_panel = current_panel
        panel_ratios.append(1)
        current_panel += 1

    # ─── Candlestick panel (always present) ─────────────────────────────────
    candle_panel = current_panel
    panel_ratios.append(4)

    if "bollinger" in indicators and "Bollinger_Upper" in data.columns:
        addplots.append(
            mpf.make_addplot(
                data["Bollinger_Upper"],
                panel=candle_panel,
                color=_PURPLE,
                linestyle="--",
                width=0.8,
            )
        )
        addplots.append(
            mpf.make_addplot(
                data["Bollinger_Lower"],
                panel=candle_panel,
                color=_PURPLE,
                linestyle="--",
                width=0.8,
            )
        )

    if "ema20" in indicators and "EMA20" in data.columns:
        addplots.append(
            mpf.make_addplot(data["EMA20"], panel=candle_panel, color=_CYAN, width=1.0)
        )

    if "ema50" in indicators and "EMA50" in data.columns:
        addplots.append(
            mpf.make_addplot(data["EMA50"], panel=candle_panel, color=_LIME, width=1.2)
        )

    if "ema200" in indicators and "EMA200" in data.columns:
        addplots.append(
            mpf.make_addplot(
                data["EMA200"], panel=candle_panel, color=_TOMATO, width=1.5
            )
        )

    # Buy / sell signal scatter markers
    if signals_data is not None and "signals" in indicators:
        buy = signals_data["Buy"].copy()
        sell = signals_data["Sell"].copy()
        if not buy.isna().all():
            addplots.append(
                mpf.make_addplot(
                    buy,
                    panel=candle_panel,
                    type="scatter",
                    markersize=80,
                    marker="^",
                    color=_LIME,
                )
            )
        if not sell.isna().all():
            addplots.append(
                mpf.make_addplot(
                    sell,
                    panel=candle_panel,
                    type="scatter",
                    markersize=80,
                    marker="v",
                    color=_RED,
                )
            )

    current_panel += 1

    # ─── Volume panel ────────────────────────────────────────────────────────
    volume_panel = None
    if "volume" in indicators and "Volume" in data.columns:
        vol_colors = [
            _GREEN if data["Close"].iloc[i] >= data["Open"].iloc[i] else _RED
            for i in range(len(data))
        ]
        addplots.append(
            mpf.make_addplot(
                data["Volume"],
                panel=current_panel,
                type="bar",
                color=vol_colors,
                ylabel="Volume",
                alpha=0.8,
            )
        )
        volume_panel = current_panel
        panel_ratios.append(1)
        current_panel += 1

    # ─── MACD panel ──────────────────────────────────────────────────────────
    macd_panel = None
    if "macd" in indicators and "MACD" in data.columns:
        hist_colors = [
            _GREEN if v >= 0 else _RED for v in data["MACD_Histogram"].fillna(0)
        ]
        addplots.extend(
            [
                mpf.make_addplot(
                    data["MACD"],
                    panel=current_panel,
                    color=_BLUE,
                    ylabel="MACD",
                    width=1.2,
                ),
                mpf.make_addplot(
                    data["MACD_Signal"], panel=current_panel, color=_ORANGE, width=1.0
                ),
                mpf.make_addplot(
                    data["MACD_Histogram"],
                    panel=current_panel,
                    type="bar",
                    color=hist_colors,
                    alpha=0.6,
                ),
            ]
        )
        macd_panel = current_panel
        panel_ratios.append(1)
        current_panel += 1

    # ─── ATR panel ───────────────────────────────────────────────────────────
    atr_panel = None
    if "atr" in indicators and "ATR" in data.columns:
        addplots.append(
            mpf.make_addplot(
                data["ATR"], panel=current_panel, color=_GOLD, ylabel="ATR", width=1.2
            )
        )
        atr_panel = current_panel
        panel_ratios.append(1)
        current_panel += 1

    # ─── Build the figure ────────────────────────────────────────────────────
    fig_height = max(8, 3 + sum(panel_ratios) * 1.6)

    plot_kwargs: dict[str, Any] = dict(
        type="candle",
        style="charles",
        title=f"\n{ticker} — Technical Analysis",
        ylabel="Price",
        volume=False,
        main_panel=candle_panel,
        panel_ratios=tuple(panel_ratios),
        figsize=(14, fig_height),
        returnfig=True,
    )
    if addplots:
        plot_kwargs["addplot"] = addplots

    fig, axs = mpf.plot(data, **plot_kwargs)
    fig.subplots_adjust(hspace=0.5)

    # ─── Post-render: threshold lines and legends ────────────────────────────

    # Oscillator panel annotations
    if oscillator_panel is not None:
        osc_ax = axs[oscillator_panel * 2]
        if has_rsi:
            osc_ax.axhline(
                30, linestyle="--", color=_LIME, linewidth=0.9, label="Oversold (30)"
            )
            osc_ax.axhline(
                70,
                linestyle="--",
                color=_TOMATO,
                linewidth=0.9,
                label="Overbought (70)",
            )
            osc_ax.set_ylim(0, 100)
        else:
            osc_ax.axhline(
                20, linestyle="--", color=_LIME, linewidth=0.9, label="Oversold (20)"
            )
            osc_ax.axhline(
                80,
                linestyle="--",
                color=_TOMATO,
                linewidth=0.9,
                label="Overbought (80)",
            )
            osc_ax.set_ylim(0, 100)
        osc_ax.legend(loc="upper left", fontsize=7)

    # Candlestick panel: EMA + BB legend
    candle_ax = axs[candle_panel * 2]
    legend_handles = []
    if "ema20" in indicators and "EMA20" in data.columns:
        legend_handles.append(
            Line2D([0], [0], color=_CYAN, linewidth=1.0, label="EMA 20")
        )
    if "ema50" in indicators and "EMA50" in data.columns:
        legend_handles.append(
            Line2D([0], [0], color=_LIME, linewidth=1.2, label="EMA 50")
        )
    if "ema200" in indicators and "EMA200" in data.columns:
        legend_handles.append(
            Line2D([0], [0], color=_TOMATO, linewidth=1.5, label="EMA 200")
        )
    if "bollinger" in indicators and "Bollinger_Upper" in data.columns:
        legend_handles.append(
            Line2D(
                [0], [0], color=_PURPLE, linestyle="--", linewidth=0.8, label="BB Bands"
            )
        )
    if "signals" in indicators and signals_data is not None:
        if not signals_data["Buy"].isna().all():
            legend_handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="^",
                    color="w",
                    markerfacecolor=_LIME,
                    markersize=8,
                    label="Buy Signal",
                    linewidth=0,
                )
            )
        if not signals_data["Sell"].isna().all():
            legend_handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="v",
                    color="w",
                    markerfacecolor=_RED,
                    markersize=8,
                    label="Sell Signal",
                    linewidth=0,
                )
            )
    if legend_handles:
        candle_ax.legend(handles=legend_handles, loc="upper left", fontsize=7)

    # Support / resistance lines
    if "support_resistance" in indicators:
        if support_levels:
            for lvl in support_levels:
                candle_ax.axhline(
                    lvl, linestyle=":", color=_LIME, alpha=0.75, linewidth=1
                )
        if resistance_levels:
            for lvl in resistance_levels:
                candle_ax.axhline(
                    lvl, linestyle=":", color=_TOMATO, alpha=0.75, linewidth=1
                )

    # MACD zero line
    if macd_panel is not None:
        axs[macd_panel * 2].axhline(
            0, linestyle="-", color="gray", linewidth=0.6, alpha=0.5
        )

    # ─── Save ────────────────────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    plot_path = os.path.join(output_dir, f"{ticker}_analysis_plots.png")
    fig.savefig(plot_path, bbox_inches="tight", dpi=150)
    plt.close(fig)

    log.info(f"Plot saved: {plot_path}")
    return plot_path
