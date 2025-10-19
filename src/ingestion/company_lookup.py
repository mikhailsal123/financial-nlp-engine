#!/usr/bin/env python3
"""
Company lookup utilities for mapping company names/tickers to CIKs using SEC EDGAR database
"""

import requests
import time
from typing import Dict, List, Optional


class CompanyLookup:
    """Utility class for looking up company information and CIKs from SEC EDGAR database"""
    
    def __init__(self):
        self.base_url = "https://www.sec.gov"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Financial Analysis Tool (contact@example.com)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def search_company(self, query: str) -> List[Dict]:
        """
        Search for companies by name or ticker using SEC EDGAR database
        
        Args:
            query: Company name or ticker symbol
            
        Returns:
            List of company dictionaries with CIK, name, and ticker
        """
        companies = []
        
        try:
            time.sleep(0.5)  # Rate limiting
            url = "https://www.sec.gov/files/company_tickers.json"
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Search through the tickers data
                for entry in data.values():
                    company_name = entry.get('title', '').upper()
                    ticker = entry.get('ticker', '').upper()
                    cik_raw = entry.get('cik_str', '')
                    
                    # Check if query matches company name or ticker
                    if (query.upper() in company_name or 
                        query.upper() in ticker or 
                        ticker == query.upper()):
                        
                        # Extract CIK from the API response
                        cik = None
                        if isinstance(cik_raw, (int, str)) and cik_raw and str(cik_raw) != '0':
                            cik = str(cik_raw).zfill(10)
                        
                        # Only add if we have a valid CIK from SEC database
                        if cik and cik != '0000000000':
                            companies.append({
                                'cik': cik,
                                'ticker': ticker,
                                'name': entry.get('title', '')
                            })
                        
                        if len(companies) >= 10:  # Limit results
                            break
                
                return companies
            
        except Exception as e:
            print(f"Error searching company tickers: {e}")
        
        # Fallback: return empty list if API fails
        print(f"Could not search for '{query}' - SEC API may be blocked")
        return []
    
    def get_company_by_ticker(self, ticker: str) -> Optional[Dict]:
        """
        Get company information by ticker symbol
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Company dictionary or None if not found
        """
        companies = self.search_company(ticker)
        
        # Filter by exact ticker match
        for company in companies:
            if company['ticker'].upper() == ticker.upper():
                return company
        
        return None
    
    def get_company_by_name(self, name: str) -> Optional[Dict]:
        """
        Get company information by company name
        
        Args:
            name: Company name
            
        Returns:
            Company dictionary or None if not found
        """
        companies = self.search_company(name)
        
        # Return the first match (most relevant)
        if companies:
            return companies[0]
        
        return None
    
    def get_cik_by_ticker(self, ticker: str) -> Optional[str]:
        """
        Get CIK by ticker symbol
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            CIK string or None if not found
        """
        company = self.get_company_by_ticker(ticker)
        return company['cik'] if company else None
    
    def get_cik_by_name(self, name: str) -> Optional[str]:
        """
        Get CIK by company name
        
        Args:
            name: Company name
            
        Returns:
            CIK string or None if not found
        """
        company = self.get_company_by_name(name)
        return company['cik'] if company else None


def get_cik_by_name_or_ticker(identifier: str) -> Optional[str]:
    """
    Get CIK by company name or ticker using SEC EDGAR database
    
    Args:
        identifier: Company name or ticker symbol
        
    Returns:
        CIK string or None if not found
    """
    lookup = CompanyLookup()
    cik = lookup.get_cik_by_ticker(identifier)
    if cik:
        return cik
    
    cik = lookup.get_cik_by_name(identifier)
    return cik


def search_companies(query: str, limit: int = 10) -> List[Dict]:
    """
    Search for companies by name or ticker using SEC EDGAR database
    
    Args:
        query: Search query
        limit: Maximum number of results
        
    Returns:
        List of company dictionaries
    """
    lookup = CompanyLookup()
    return lookup.search_company(query)[:limit]


if __name__ == "__main__":
    # Example usage
    lookup = CompanyLookup()
    
    # Search by ticker
    print("Searching for NVIDIA by ticker 'NVDA':")
    company = lookup.get_company_by_ticker('NVDA')
    print(f"Result: {company}")
    
    # Search by name
    print("\nSearching for Apple by name:")
    company = lookup.get_company_by_name('Apple')
    print(f"Result: {company}")
    
    # Quick lookup
    print(f"\nQuick lookup for AAPL: {get_cik_by_name_or_ticker('AAPL')}")
    print(f"Quick lookup for Microsoft: {get_cik_by_name_or_ticker('Microsoft')}")