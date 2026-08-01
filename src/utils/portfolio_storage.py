# Import standard library packages.
import json
from pathlib import Path

# Import local packages.
from src.models.portfolio import Portfolio

# Same Path-based cache file approach as stock_analysis.py's ticker cache,
# just a different file in the same cache/ directory.
_PORTFOLIO_CACHE_FILE = Path("cache/portfolios.json")


def load_portfolios() -> list[Portfolio]:
    """
    Read persisted portfolios from disk.

    Returns:
        The cached portfolios, or an empty list if the cache is missing,
        unreadable, or contains invalid data. A single malformed
        portfolio entry is skipped rather than discarding the whole file.
    """
    if not _PORTFOLIO_CACHE_FILE.exists():
        return []

    try:
        payload = json.loads(_PORTFOLIO_CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    raw_portfolios = payload.get("portfolios", [])
    portfolios: list[Portfolio] = []

    for raw in raw_portfolios:
        try:
            portfolios.append(Portfolio.model_validate(raw))
        except Exception:
            continue

    return portfolios


def save_portfolios(portfolios: list[Portfolio]) -> None:
    """
    Persist the current portfolio list to disk.

    Args:
        portfolios: The full list of portfolios to save (overwrites
            whatever was previously cached).
    """
    _PORTFOLIO_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "portfolios": [portfolio.model_dump(mode="json") for portfolio in portfolios]
    }

    _PORTFOLIO_CACHE_FILE.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
