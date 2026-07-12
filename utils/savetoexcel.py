import logging

import pandas as pd

log = logging.getLogger(__name__)


def save_to_excel(
    analyzed_data: dict, file_path: str, range_stats: dict | None = None
) -> None:
    """
    Save all analyzed ticker DataFrames to separate sheets in a single Excel
    file. When range_stats is provided, a "Summary" sheet listing each
    ticker's historical high/low for the selected date range is written first.
    """
    range_stats = range_stats or {}

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        summary_rows = []
        for ticker in analyzed_data:
            rs = range_stats.get(ticker)
            if not rs:
                continue
            summary_rows.append(
                {
                    "Ticker": ticker,
                    "Period High": rs.get("period_high"),
                    "High Date": rs.get("period_high_date"),
                    "Period Low": rs.get("period_low"),
                    "Low Date": rs.get("period_low_date"),
                    "Current Close": rs.get("current_close"),
                    "% From High": rs.get("pct_from_high"),
                    "% From Low": rs.get("pct_from_low"),
                }
            )
        if summary_rows:
            pd.DataFrame(summary_rows).to_excel(
                writer, sheet_name="Summary", index=False
            )

        for ticker, data in analyzed_data.items():
            data.to_excel(writer, sheet_name=ticker)

    log.info(f"Stock data saved to {file_path}")
