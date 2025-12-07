"""
Finnhub API Client
Simple client for fetching financial data from Finnhub API
"""
import os
import requests
from typing import Dict, Optional, Any, List
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FinnhubClient:
    """Client for Finnhub API"""
    
    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY")
        self.base_url = "https://finnhub.io/api/v1"
        
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request"""
        if not self.api_key:
            logger.warning("Finnhub API key not set")
            return None
            
        if params is None:
            params = {}
        params['token'] = self.api_key
        
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Finnhub API request failed: {e}")
            return None
    
    def fetch_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time quote"""
        data = self._make_request('quote', {'symbol': symbol})
        if data and 'c' in data:
            return {
                'symbol': symbol,
                'price': data.get('c', 0),
                'change': data.get('d', 0),
                'change_percent': data.get('dp', 0),
                'high': data.get('h', 0),
                'low': data.get('l', 0),
                'open': data.get('o', 0),
                'previous_close': data.get('pc', 0),
                'timestamp': data.get('t', 0),
            }
        return None
    
    def fetch_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch company profile"""
        data = self._make_request('stock/profile2', {'symbol': symbol})
        if data:
            return {
                'name': data.get('name'),
                'ticker': data.get('ticker'),
                'exchange': data.get('exchange'),
                'industry': data.get('finnhubIndustry'),
                'sector': data.get('sector'),
                'market_cap': data.get('marketCapitalization'),
                'weburl': data.get('weburl'),
                'logo': data.get('logo'),
            }
        return None
    
    def fetch_peers(self, symbol: str) -> List[str]:
        """Fetch peer companies"""
        data = self._make_request('stock/peers', {'symbol': symbol})
        if data and isinstance(data, list):
            return data
        return []
    
    def fetch_news(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Fetch company news"""
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)
        
        params = {
            'symbol': symbol,
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d')
        }
        data = self._make_request('company-news', params)
        if data and isinstance(data, list):
            return data[:20]  # Limit to 20 most recent
        return []
    
    def fetch_financials(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch financial statements"""
        # Try to get basic financial metrics
        data = self._make_request('stock/metric', {
            'symbol': symbol,
            'metric': 'all'
        })
        return data

