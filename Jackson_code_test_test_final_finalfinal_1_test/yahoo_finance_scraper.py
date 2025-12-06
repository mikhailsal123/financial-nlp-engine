#!/usr/bin/env python3
"""
Yahoo Finance scraper for fetching company financial data
Similar structure to scrap_sec.py but for Yahoo Finance API
"""

import yfinance as yf
import json
import os
from datetime import datetime
from typing import Dict, List, Optional


def get_company_info(ticker: str) -> Optional[Dict]:
    """
    Fetch basic company information
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
    
    Returns:
        Dictionary with company info or None if failed
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Extract key information
        company_data = {
            'ticker': ticker,
            'company_name': info.get('longName', 'Unknown'),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'market_cap': info.get('marketCap', 0),
            'website': info.get('website', ''),
            'description': info.get('longBusinessSummary', ''),
            'employees': info.get('fullTimeEmployees', 0),
            'country': info.get('country', 'Unknown')
        }
        
        return company_data
    except Exception as e:
        print(f"Error fetching company info: {e}")
        return None


def get_financial_statements(ticker: str) -> Dict:
    """
    Fetch financial statements (income, balance sheet, cash flow)
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Dictionary containing all financial statements
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Helper function to convert DataFrame with Timestamp columns to dict
        def df_to_dict(df):
            if df.empty:
                return {}
            # Convert column names (dates) to strings first
            df.columns = df.columns.astype(str)
            return df.to_dict()
        
        financial_data = {
            'income_statement': df_to_dict(stock.financials),
            'balance_sheet': df_to_dict(stock.balance_sheet),
            'cash_flow': df_to_dict(stock.cashflow),
            'quarterly_income': df_to_dict(stock.quarterly_financials)
        }
        
        return financial_data
    except Exception as e:
        print(f"Error fetching financial statements: {e}")
        return {}


def get_earnings_history(ticker: str) -> Dict:
    """
    Fetch earnings history and estimates
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Dictionary with earnings data
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Helper function to safely convert DataFrames
        def safe_to_dict(df):
            if df is None or (hasattr(df, 'empty') and df.empty):
                return {}
            # Convert any Timestamp columns/index to strings
            df = df.copy()
            if hasattr(df, 'columns'):
                df.columns = df.columns.astype(str)
            if hasattr(df, 'index'):
                df.index = df.index.astype(str)
            return df.to_dict()
        
        earnings_data = {
            'earnings': safe_to_dict(stock.earnings) if hasattr(stock, 'earnings') else {},
            'quarterly_earnings': safe_to_dict(stock.quarterly_earnings) if hasattr(stock, 'quarterly_earnings') else {},
            'earnings_dates': safe_to_dict(stock.earnings_dates) if hasattr(stock, 'earnings_dates') else {}
        }
        
        return earnings_data
    except Exception as e:
        print(f"Error fetching earnings history: {e}")
        return {}


def get_news(ticker: str, max_news: int = 10) -> List[Dict]:
    """
    Fetch recent news articles for the company
    
    Args:
        ticker: Stock ticker symbol
        max_news: Maximum number of news articles to fetch
    
    Returns:
        List of news articles with title, link, and publisher
    """
    try:
        stock = yf.Ticker(ticker)
        news = stock.news[:max_news] if stock.news else []
        
        formatted_news = []
        for article in news:
            formatted_news.append({
                'title': article.get('title', ''),
                'publisher': article.get('publisher', ''),
                'link': article.get('link', ''),
                'published': datetime.fromtimestamp(article.get('providerPublishTime', 0)).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return formatted_news
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []


def execute_scraping(
    ticker: str,
    output_dir: str = 'data/raw/yahoo_finance',
    include_news: bool = True,
    max_news: int = 10
) -> Dict[str, str]:
    """
    Main function to scrape all Yahoo Finance data for a ticker
    
    Args:
        ticker: Stock ticker symbol
        output_dir: Directory to save output files
        include_news: Whether to fetch news articles
        max_news: Maximum number of news articles
    
    Returns:
        Dictionary with paths to saved files
    """
    ticker = ticker.upper()
    print(f"\nFetching data for {ticker}...")
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    saved_files = {}
    
    # 1. Company Info
    print("  → Fetching company information...")
    company_info = get_company_info(ticker)
    if company_info:
        filepath = os.path.join(output_dir, f"{ticker}_company_info.json")
        with open(filepath, 'w') as f:
            json.dump(company_info, f, indent=2, default=str)
        saved_files['company_info'] = filepath
        print(f"    ✓ Saved to {filepath}")
    
    # 2. Financial Statements
    print("  → Fetching financial statements...")
    financials = get_financial_statements(ticker)
    if financials:
        filepath = os.path.join(output_dir, f"{ticker}_financials.json")
        with open(filepath, 'w') as f:
            json.dump(financials, f, indent=2, default=str)
        saved_files['financials'] = filepath
        print(f"    ✓ Saved to {filepath}")
    
    # 3. Earnings History
    print("  → Fetching earnings history...")
    earnings = get_earnings_history(ticker)
    if earnings:
        filepath = os.path.join(output_dir, f"{ticker}_earnings.json")
        with open(filepath, 'w') as f:
            json.dump(earnings, f, indent=2, default=str)
        saved_files['earnings'] = filepath
        print(f"    ✓ Saved to {filepath}")
    
    # 4. News Articles
    if include_news:
        print(f"  → Fetching {max_news} recent news articles...")
        news = get_news(ticker, max_news)
        if news:
            filepath = os.path.join(output_dir, f"{ticker}_news.json")
            with open(filepath, 'w') as f:
                json.dump(news, f, indent=2, default=str)
            saved_files['news'] = filepath
            print(f"    ✓ Saved to {filepath}")
    
    print(f"\n✓ Completed! Saved {len(saved_files)} files")
    return saved_files


def main():
    """Command-line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Scrape financial data from Yahoo Finance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all data for Apple
  python yahoo_finance_scraper.py --ticker AAPL
  
  # Fetch data without news
  python yahoo_finance_scraper.py --ticker MSFT --no-news
  
  # Fetch with custom output directory
  python yahoo_finance_scraper.py --ticker NVDA --output-dir ./my_data
  
  # Fetch more news articles
  python yahoo_finance_scraper.py --ticker TSLA --max-news 20
        """
    )
    
    parser.add_argument('--ticker', required=True, help='Stock ticker symbol (e.g., AAPL, MSFT)')
    parser.add_argument('--output-dir', default='data/raw/yahoo_finance',
                       help='Output directory for downloaded data (default: data/raw/yahoo_finance)')
    parser.add_argument('--no-news', action='store_true',
                       help='Skip fetching news articles')
    parser.add_argument('--max-news', type=int, default=10,
                       help='Maximum number of news articles to fetch (default: 10)')
    
    args = parser.parse_args()
    
    try:
        execute_scraping(
            ticker=args.ticker,
            output_dir=args.output_dir,
            include_news=not args.no_news,
            max_news=args.max_news
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()