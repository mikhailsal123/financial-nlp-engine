"""
Client for interacting with the Alpha Vantage API without modifying existing
code paths. This module adds a third market data source (alongside FRED and
Yahoo Finance) so the NLP pipeline can be linked to current and historical
market context without replacing any existing functionality.

The client focuses on safe defaults:
- Explicit API key handling (via constructor or ALPHA_VANTAGE_API_KEY env var).
- Thin HTTP wrapper with helpful errors.
- Convenience helpers that return pandas DataFrames for immediate analysis.
- Basic rate limiting to avoid hitting the free tier throttle (5 requests per
  minute, 500 per day).

Example
-------
>>> from src.ingestion.alpha_vantage_client import AlphaVantageClient
>>> client = AlphaVantageClient()
>>> prices = client.fetch_time_series_daily("AAPL")
>>> earnings = client.fetch_earnings("AAPL")
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd
import requests


class AlphaVantageError(RuntimeError):
    """Raised when the Alpha Vantage API returns an error payload."""


@dataclass
class AlphaVantageClient:
    """
    Lightweight Alpha Vantage client with sensible defaults.

    Parameters
    ----------
    api_key:
        The Alpha Vantage API key. If omitted, the client will look for the
        ``ALPHA_VANTAGE_API_KEY`` environment variable.
    session:
        Optional ``requests.Session`` for connection pooling. Supplying a
        session can significantly reduce latency when making many sequential
        calls.
    throttle_per_minute:
        Maximum number of requests allowed per minute. Defaults to 5 to align
        with the public free tier. Set ``None`` to disable client-side
        throttling (not recommended).
    """

    api_key: Optional[str] = None
    session: Optional[requests.Session] = None
    throttle_per_minute: Optional[int] = 5

    _last_request_ts: float = 0.0

    BASE_URL: str = "https://www.alphavantage.co/query"

    def __post_init__(self) -> None:
        if not self.api_key:
            self.api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Alpha Vantage API key is required. Provide it via constructor "
                "or set the ALPHA_VANTAGE_API_KEY environment variable."
            )

        if self.session is None:
            self.session = requests.Session()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def fetch_time_series_daily(
        self, symbol: str, output_size: str = "compact", adjusted: bool = True
    ) -> pd.DataFrame:
        """
        Fetch daily time-series data for a ticker as a DataFrame.

        Parameters
        ----------
        symbol:
            The ticker symbol (e.g., ``"AAPL"``).
        output_size:
            ``"compact"`` returns the last 100 data points; ``"full"`` returns
            the full-length time series (subject to API limits).
        adjusted:
            Whether to request adjusted close prices.
        """

        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED" if adjusted else "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": output_size,
        }
        payload = self._request(params)
        key = next((k for k in payload if "Time Series" in k), None)
        if not key:
            raise AlphaVantageError("Time series data not found in response.")

        df = pd.DataFrame.from_dict(payload[key], orient="index", dtype=float)
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        df.rename(columns=self._normalize_column_names, inplace=True)
        return df

    def fetch_company_overview(self, symbol: str) -> Dict[str, str]:
        """
        Fetch high-level company fundamentals (sector, market cap, beta, etc.).
        """

        payload = self._request({"function": "OVERVIEW", "symbol": symbol})
        if not payload:
            raise AlphaVantageError("Company overview response is empty.")
        return payload

    def fetch_earnings(self, symbol: str) -> pd.DataFrame:
        """
        Fetch annual and quarterly earnings data as a DataFrame.
        """

        payload = self._request({"function": "EARNINGS", "symbol": symbol})
        if "quarterlyEarnings" not in payload:
            raise AlphaVantageError("Earnings data not found in response.")

        quarterly = pd.DataFrame(payload["quarterlyEarnings"])
        quarterly["reportedDate"] = pd.to_datetime(quarterly["reportedDate"])
        quarterly.sort_values("reportedDate", inplace=True)
        return quarterly

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _request(self, params: Dict[str, str]) -> Dict:
        params_with_key = {**params, "apikey": self.api_key}
        self._respect_throttle()
        response = self.session.get(self.BASE_URL, params=params_with_key, timeout=30)
        response.raise_for_status()

        payload: Dict = response.json()
        if "Error Message" in payload:
            raise AlphaVantageError(payload["Error Message"])
        if "Note" in payload and "frequency" in payload["Note"].lower():
            # Alpha Vantage uses a human-readable note to indicate throttling.
            raise AlphaVantageError(payload["Note"])
        return payload

    def _respect_throttle(self) -> None:
        if self.throttle_per_minute is None:
            return

        elapsed = time.monotonic() - self._last_request_ts
        min_interval = 60.0 / max(self.throttle_per_minute, 1)
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_ts = time.monotonic()

    @staticmethod
    def _normalize_column_names(column: str) -> str:
        # Columns are typically numbered keys like "1. open". We drop the prefix
        # number and period to yield clean names such as "open", "high", etc.
        return column.split(" ", 1)[-1]