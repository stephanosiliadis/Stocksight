import os
import logging

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

log = logging.getLogger(__name__)

# Distinct colors that work on both light and dark backgrounds
_PALETTE = [
    "#2196F3",
    "#FF5722",
    "#4CAF50",
    "#9C27B0",
    "#FF9800",
    "#00BCD4",
    "#F44336",
    "#8BC34A",
]


def generate_comparison_plot(
    analyzed_data: dict,
    tickers: list,
    output_dir: str = "data",
) -> str:
    """
    Generate a normalized relative-performance chart for multiple tickers.

    Each series is re-based to 100 at the first data point so percentage
    gains/losses can be compared directly regardless of absolute price.
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    plotted = 0
    for idx, ticker in enumerate(tickers):
        data = analyzed_data.get(ticker)
        if data is None or data.empty:
            log.warning(f"No data for {ticker} — skipping comparison.")
            continue

        close = data["Close"].dropna()
        if close.empty or close.iloc[0] == 0:
            continue

        normalized = (close / close.iloc[0]) * 100
        color = _PALETTE[idx % len(_PALETTE)]
        ax.plot(
            normalized.index,
            normalized.values,
            label=ticker,
            color=color,
            linewidth=1.8,
        )
        plotted += 1

    if plotted == 0:
        log.warning("No valid tickers to plot for comparison.")
        plt.close(fig)
        return ""

    # Baseline
    ax.axhline(100, linestyle="--", color="#555555", linewidth=0.9, alpha=0.7)

    # Formatting
    ax.set_title(
        "Relative Price Performance (Normalized to 100)",
        fontsize=14,
        color="white",
        pad=12,
    )
    ax.set_xlabel("Date", color="#aaaaaa", fontsize=10)
    ax.set_ylabel("Indexed Performance", color="#aaaaaa", fontsize=10)
    ax.tick_params(colors="#aaaaaa")
    ax.spines["bottom"].set_color("#333355")
    ax.spines["left"].set_color("#333355")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, color="#2a2a4a", linewidth=0.6)

    # Y-axis: show as % change from baseline
    def pct_fmt(val, _):
        return f"{val - 100:+.1f}%"

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(pct_fmt))

    legend = ax.legend(loc="upper left", fontsize=9, framealpha=0.3)
    for text in legend.get_texts():
        text.set_color("white")

    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    plot_path = os.path.join(output_dir, "comparison_chart.png")
    fig.savefig(plot_path, bbox_inches="tight", dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)

    log.info(f"Comparison chart saved to {plot_path}")
    return plot_path
