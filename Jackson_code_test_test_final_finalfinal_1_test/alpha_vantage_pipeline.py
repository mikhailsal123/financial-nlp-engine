"""
Thin convenience layer to align the Alpha Vantage client with the rest of the
repo's ingestion helpers. These functions expose simple, parser-style entry
points (function-in, structured-data-out) without modifying the underlying
client or any existing code paths.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional

import pandas as pd

from .alpha_vantage_client import AlphaVantageClient, AlphaVantageError


@lru_cache(maxsize=1)
def _shared_client(api_key: Optional[str] = None) -> AlphaVantageClient:
    """Return a shared client instance to reuse HTTP sessions across calls."""

    return AlphaVantageClient(api_key=api_key)


def load_daily_prices(
    symbol: str, output_size: str = "compact", adjusted: bool = True
) -> pd.DataFrame:
    """Fetch daily OHLCV data in a consistent, parser-friendly shape."""

    client = _shared_client()
    df = client.fetch_time_series_daily(symbol, output_size=output_size, adjusted=adjusted)
    df.index.name = "date"
    # Ensure column order is stable for downstream joins/comparisons.
    preferred_order = ["open", "high", "low", "close", "adjusted close", "volume"]
    ordered_cols = [col for col in preferred_order if col in df.columns]
    df = df[ordered_cols + [c for c in df.columns if c not in ordered_cols]]
    return df


def load_company_snapshot(symbol: str) -> Dict[str, str]:
    """Return core company metadata (sector, market cap, beta, etc.)."""

    client = _shared_client()
    overview = client.fetch_company_overview(symbol)
    # Mirror other parsers by keeping the payload simple for downstream merging.
    return {k: str(v) for k, v in overview.items() if v is not None}


def load_quarterly_earnings(symbol: str) -> pd.DataFrame:
    """Return quarterly earnings with predictable column names and ordering."""

    client = _shared_client()
    earnings = client.fetch_earnings(symbol)
    # Align column order to emphasize timing and EPS surprise metrics.
    preferred_order = [
        "reportedDate",
        "fiscalDateEnding",
        "reportedEPS",
        "estimatedEPS",
        "surprise",
        "surprisePercentage",
    ]
    ordered_cols = [col for col in preferred_order if col in earnings.columns]
    return earnings[ordered_cols + [c for c in earnings.columns if c not in ordered_cols]]


__all__ = [
    "load_daily_prices",
    "load_company_snapshot",
    "load_quarterly_earnings",
    "AlphaVantageClient",
    "AlphaVantageError",
]