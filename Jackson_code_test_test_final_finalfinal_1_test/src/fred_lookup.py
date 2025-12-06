import os
import requests

FRED_BASE_URL = "https://api.stlouisfed.org/fred"


def _get_api_key() -> str:
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY missing")
    return key


def search_series(search_text: str, limit: int = 10) -> list[dict]:
    """
    Searches FRED for matching series.

    NOTE:
    All downloaded series now automatically include:
    - change  (numeric difference from previous)
    - label   ("good" / "bad" / "neutral")              # >>> ADDED
    """
    api_key = _get_api_key()
    url = f"{FRED_BASE_URL}/series/search"

    params = {
        "search_text": search_text,
        "api_key": api_key,
        "file_type": "json",
        "limit": limit,
    }

    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    return data.get("seriess", [])