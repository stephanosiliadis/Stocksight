# Import standard library packages.
import os

# Import third party packages.
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# Distinct colors for multiple series.
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


def create_comparison_chart(
    normalized_data: dict[str, pd.Series],
    output_dir: str = "data",
) -> str | None:
    """
    Create a normalized relative-performance comparison chart.

    Each ticker is plotted with its first available price normalized to 100,
    allowing comparison of relative gains and losses regardless of absolute
    share price.

    Args:
        normalized_data: Dictionary mapping ticker symbols to normalized
            performance series.
        output_dir: Directory where the generated chart is saved.

    Returns:
        Path to the generated chart image, or None if no valid data exists.
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    plotted = 0

    for idx, (ticker, data) in enumerate(normalized_data.items()):
        if data is None:
            continue

        ax.plot(
            np.asarray(data.index),
            data.to_numpy(dtype=float),
            label=ticker,
            color=_PALETTE[idx % len(_PALETTE)],
            linewidth=1.8,
        )

        plotted += 1

    if plotted == 0:
        plt.close(fig)
        return None

    ax.axhline(
        100,
        linestyle="--",
        color="#555555",
        linewidth=0.9,
        alpha=0.7,
    )

    ax.set_title(
        "Relative Price Performance (Normalized to 100)",
        fontsize=14,
        pad=12,
    )

    ax.set_xlabel("Date")
    ax.set_ylabel("Indexed Performance")

    ax.grid(True, linewidth=0.6)

    def percentage_formatter(value, _):
        return f"{value - 100:+.1f}%"

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(percentage_formatter))

    ax.legend(
        loc="upper left",
        fontsize=9,
    )

    plt.tight_layout()

    os.makedirs(output_dir, exist_ok=True)

    chart_path = os.path.join(
        output_dir,
        "comparison_chart.png",
    )

    fig.savefig(
        chart_path,
        bbox_inches="tight",
        dpi=150,
    )

    plt.close(fig)

    return chart_path
