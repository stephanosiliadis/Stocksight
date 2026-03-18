import logging

import pandas as pd

log = logging.getLogger(__name__)


def save_to_excel(analyzed_data: dict, file_path: str) -> None:
    """
    Save all analyzed ticker DataFrames to separate sheets in a single Excel file.
    """
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        for ticker, data in analyzed_data.items():
            data.to_excel(writer, sheet_name=ticker)

    log.info(f"Stock data saved to {file_path}")
