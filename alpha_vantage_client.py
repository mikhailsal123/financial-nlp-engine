"""
Alpha Vantage API Client
Simple client for fetching stock data from Alpha Vantage API
"""
import os
import requests
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

class AlphaVantageClient:
    """Client for Alpha Vantage API"""
    
    def __init__(self):
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.base_url = "https://www.alphavantage.co/query"
        
    def fetch_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time quote"""
        if not self.api_key:
            logger.warning("Alpha Vantage API key not set")
            return None
            
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Global Quote' in data:
                quote = data['Global Quote']
                return {
                    'symbol': quote.get('01. symbol'),
                    'price': float(quote.get('05. price', 0)),
                    'change': float(quote.get('09. change', 0)),
                    'change_percent': quote.get('10. change percent', '0%').replace('%', ''),
                    'volume': int(quote.get('06. volume', 0)),
                    'high': float(quote.get('03. high', 0)),
                    'low': float(quote.get('04. low', 0)),
                    'open': float(quote.get('02. open', 0)),
                }
        except Exception as e:
            logger.warning(f"Alpha Vantage quote fetch failed: {e}")
        return None
    
    def fetch_overview(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch company overview"""
        if not self.api_key:
            return None
            
        try:
            params = {
                'function': 'OVERVIEW',
                'symbol': symbol,
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'Symbol' in data:
                return {
                    'name': data.get('Name'),
                    'sector': data.get('Sector'),
                    'industry': data.get('Industry'),
                    'market_cap': data.get('MarketCapitalization'),
                    'pe_ratio': data.get('PERatio'),
                    'eps': data.get('EPS'),
                    'dividend_yield': data.get('DividendYield'),
                    '52_week_high': data.get('52WeekHigh'),
                    '52_week_low': data.get('52WeekLow'),
                }
        except Exception as e:
            logger.warning(f"Alpha Vantage overview fetch failed: {e}")
        return None

