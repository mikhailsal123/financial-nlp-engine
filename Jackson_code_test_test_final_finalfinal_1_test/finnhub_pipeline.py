"""Pipeline-aligned helpers for Finnhub ingestion.

These helpers mirror existing parser conventions while keeping the original code
unchanged. They wrap :class:`~src.ingestion.finnhub_client.FinnhubClient` to
return pandas-ready structures for quotes, company snapshots, news, and
financial statements.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional

import pandas as pd

from src.ingestion.finnhub_client import FinnhubClient

DEFAULT_NEWS_LOOKBACK_DAYS = 7


def _ensure_client(client: Optional[FinnhubClient]) -> FinnhubClient:
    return client if client is not None else FinnhubClient()


def fetch_realtime_quote(symbol: str, client: Optional[FinnhubClient] = None) -> pd.DataFrame:
    """Return the latest quote as a single-row DataFrame."""

    active_client = _ensure_client(client)
    quote = active_client.fetch_quote(symbol)
    frame = pd.DataFrame([quote])
    frame.insert(0, "symbol", symbol)
    return frame


def fetch_company_snapshot(symbol: str, client: Optional[FinnhubClient] = None) -> pd.DataFrame:
    """Combine profile and quote data into a unified snapshot."""

    active_client = _ensure_client(client)
    profile = active_client.fetch_company_profile(symbol)
    quote = active_client.fetch_quote(symbol)
    merged = {**profile, **quote}
    return pd.DataFrame([merged])


def fetch_recent_company_news(
    symbol: str, days: int = DEFAULT_NEWS_LOOKBACK_DAYS, client: Optional[FinnhubClient] = None
) -> pd.DataFrame:
    """Fetch and sort recent company news (latest first)."""

    active_client = _ensure_client(client)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    news_items = active_client.fetch_company_news(symbol, start_date.isoformat(), end_date.isoformat())
    frame = pd.DataFrame(news_items)
    if not frame.empty and "datetime" in frame.columns:
        frame.sort_values(by="datetime", ascending=False, inplace=True)
    frame.insert(0, "symbol", symbol)
    return frame


def fetch_financials_dataframe(
    symbol: str,
    statement_type: str = "bs",
    frequency: str = "annual",
    client: Optional[FinnhubClient] = None,
) -> pd.DataFrame:
    """Return financial statement data as a DataFrame."""

    active_client = _ensure_client(client)
    payload = active_client.fetch_financials(symbol, statement_type=statement_type, frequency=frequency)
    data = payload.get("data", []) if isinstance(payload, dict) else []
    frame = pd.DataFrame(data)
    frame.insert(0, "symbol", symbol)
    return frame


def fetch_earnings_calendar_dataframe(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 50,
    client: Optional[FinnhubClient] = None,
) -> pd.DataFrame:
    """Return earnings calendar entries for the symbol."""

    active_client = _ensure_client(client)
    earnings = active_client.fetch_earnings_calendar(symbol, start_date=start_date, end_date=end_date, limit=limit)
    frame = pd.DataFrame(earnings)
    if not frame.empty and "date" in frame.columns:
        frame.sort_values(by="date", ascending=False, inplace=True)
    frame.insert(0, "symbol", symbol)
    return frame


def fetch_symbol_peers(symbol: str, client: Optional[FinnhubClient] = None) -> Iterable[str]:
    """Return peer tickers for the requested symbol."""

    active_client = _ensure_client(client)
    return active_client.fetch_symbol_peers(symbol)