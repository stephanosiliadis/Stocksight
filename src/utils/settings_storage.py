# Import standard library packages.
import json
from pathlib import Path

# Import local packages.
from src.models.app_settings import AppSettings

# Same Path-based cache file approach as stock_analysis.py's ticker cache,
# portfolio_storage.py, and watchlist_storage.py.
_SETTINGS_CACHE_FILE = Path("cache/settings.json")


def load_settings() -> AppSettings:
    """
    Read persisted settings from disk.

    Returns:
        The cached AppSettings, or a fresh default AppSettings() if the
        cache is missing, unreadable, or contains invalid data -- so a
        user who has never visited Settings gets the same defaults the
        app always had.
    """
    if not _SETTINGS_CACHE_FILE.exists():
        return AppSettings()

    try:
        payload = json.loads(_SETTINGS_CACHE_FILE.read_text(encoding="utf-8"))
        return AppSettings.model_validate(payload)
    except Exception:
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    """Persist the given settings to disk."""
    _SETTINGS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_CACHE_FILE.write_text(
        json.dumps(settings.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
