# Import standard library packages.
import json
from pathlib import Path

# Same Path-based cache file approach as stock_analysis.py's ticker cache
# and portfolio_storage.py's portfolio cache.
_WATCHLIST_CACHE_FILE = Path("cache/watchlist.json")


def load_watchlist() -> list[str]:
    """
    Read the persisted watchlist from disk.

    Returns:
        The cached tickers, or an empty list if the cache is missing,
        unreadable, or contains invalid data.
    """
    if not _WATCHLIST_CACHE_FILE.exists():
        return []

    try:
        payload = json.loads(_WATCHLIST_CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    tickers = payload.get("tickers", [])
    return [ticker for ticker in tickers if isinstance(ticker, str)]


def save_watchlist(tickers: list[str]) -> None:
    """
    Persist the current watchlist to disk.

    Args:
        tickers: The full watchlist (overwrites whatever was cached).
    """
    _WATCHLIST_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _WATCHLIST_CACHE_FILE.write_text(
        json.dumps({"tickers": list(tickers)}, indent=2),
        encoding="utf-8",
    )
