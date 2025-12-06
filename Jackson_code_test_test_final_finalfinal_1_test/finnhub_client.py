"""Lightweight Finnhub client with throttling and structured helpers.

This module adds Finnhub as an additional market data source alongside existing
parsers without modifying current ingestion code. It emphasizes reusability,
rate-aware requests, and pandas-friendly payloads for downstream pipelines.

Example:
    from src.ingestion.finnhub_client import FinnhubClient

    client = FinnhubClient()
    quote = client.fetch_quote("AAPL")
    profile = client.fetch_company_profile("AAPL")
    news_items = client.fetch_company_news("AAPL", "2024-01-01", "2024-02-01")
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional

import requests


class FinnhubClient:
    """API client for Finnhub with minimal dependencies and safe defaults.

    Attributes:
        api_key: Authentication token (also read from ``FINNHUB_API_KEY``).
        base_url: Finnhub REST base URL.
        min_interval: Minimum seconds between API calls to respect rate limits.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        session: Optional[requests.Session] = None,
        base_url: str = "https://finnhub.io/api/v1",
        min_interval: float = 0.25,
    ) -> None:
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            raise ValueError("Finnhub API key is required (set FINNHUB_API_KEY or pass api_key)")

        self.base_url = base_url.rstrip("/")
        self.min_interval = float(min_interval)
        self._session = session or requests.Session()
        self._last_request_at: Optional[float] = None

    def close(self) -> None:
        """Close the underlying HTTP session."""

        self._session.close()

    def _throttle(self) -> None:
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def _request(self, path: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        self._throttle()
        url = f"{self.base_url}/{path.lstrip('/') }"
        merged_params: MutableMapping[str, Any] = {"token": self.api_key}
        if params:
            merged_params.update(params)

        response = self._session.get(url, params=merged_params, timeout=15)
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, Mapping) and payload.get("error"):
            raise ValueError(f"Finnhub error: {payload['error']}")
        return payload

    def fetch_quote(self, symbol: str) -> Mapping[str, Any]:
        """Fetch real-time quote data for a ticker.

        Returns keys like ``c`` (current), ``o`` (open), ``h`` (high), ``l`` (low), and ``t`` (timestamp).
        """

        return self._request("quote", {"symbol": symbol})

    def fetch_company_profile(self, symbol: str) -> Mapping[str, Any]:
        """Fetch company profile snapshot (name, industry, exchange, etc.)."""

        return self._request("stock/profile2", {"symbol": symbol})

    def fetch_company_news(self, symbol: str, start_date: str, end_date: str) -> List[Mapping[str, Any]]:
        """Fetch company-specific news between two ISO dates (YYYY-MM-DD)."""

        return self._request("company-news", {"symbol": symbol, "from": start_date, "to": end_date})

    def fetch_earnings_calendar(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 50
    ) -> List[Mapping[str, Any]]:
        """Fetch upcoming or historical earnings calendar entries for a ticker."""

        params: Dict[str, Any] = {"symbol": symbol, "limit": limit}
        if start_date:
            params["from"] = start_date
        if end_date:
            params["to"] = end_date
        return self._request("calendar/earnings", params).get("earningsCalendar", [])

    def fetch_financials(self, symbol: str, statement_type: str = "bs", frequency: str = "annual") -> Mapping[str, Any]:
        """Fetch financial statements (balance sheet, income statement, or cashflow).

        Args:
            statement_type: ``bs`` for balance sheet, ``ic`` for income statement, ``cf`` for cashflow.
            frequency: ``annual`` or ``quarterly``.
        """

        params = {"symbol": symbol, "statement": statement_type, "freq": frequency}
        return self._request("stock/financials", params)

    def fetch_symbol_peers(self, symbol: str) -> Iterable[str]:
        """Return peer tickers for the requested symbol."""

        peers = self._request("stock/peers", {"symbol": symbol})
        if isinstance(peers, list):
            return peers
        return []