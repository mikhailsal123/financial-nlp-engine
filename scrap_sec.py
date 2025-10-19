#!/usr/bin/env python3
"""
Command-line tool for scraping SEC EDGAR 10-Q statements by firm/CIK
"""

import argparse
import sys
import os
from typing import List, Optional

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ingestion.sec_scraper import execute_scraping, get_company_name
from ingestion.company_lookup import get_cik_by_name_or_ticker, search_companies, COMMON_COMPANIES


def main():
    parser = argparse.ArgumentParser(
        description='Extract 10-Q statements by firm/CIK via SEC EDGAR',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract 10-Q filings by CIK
  python scrap_sec.py --cik 0001045810 --max-filings 5
  
  # Extract by ticker symbol
  python scrap_sec.py --ticker NVDA --max-filings 3
  
  # Extract by company name
  python scrap_sec.py --company "NVIDIA Corporation" --max-filings 2
  
  # Search for companies
  python scrap_sec.py --search "Apple"
  
  # Extract with custom output directory
  python scrap_sec.py --ticker AAPL --output-dir ./my_reports --max-filings 5
        """
    )
    
    # Input options (mutually exclusive, but not required if --list-common is used)
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument('--cik', help='Company CIK (10-digit number)')
    input_group.add_argument('--ticker', help='Stock ticker symbol (e.g., AAPL, MSFT)')
    input_group.add_argument('--company', help='Company name')
    input_group.add_argument('--search', help='Search for companies by name or ticker')
    
    # Output options
    parser.add_argument('--max-filings', type=int, default=5,
                       help='Maximum number of 10-Q filings to download (default: 5)')
    parser.add_argument('--output-dir', default='data/processed/earnings_reports',
                       help='Output directory for downloaded filings (default: data/processed/earnings_reports)')
    parser.add_argument('--forms', nargs='+', default=['10-Q'],
                       help='Form types to download (default: 10-Q)')
    
    # Additional options
    parser.add_argument('--list-common', action='store_true',
                       help='List common company tickers and CIKs')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Handle list common companies
    if args.list_common:
        print("Common Company Tickers and CIKs:")
        print("=" * 40)
        for ticker, cik in sorted(COMMON_COMPANIES.items()):
            print(f"{ticker:8} -> {cik}")
        return
    
    # Handle search
    if args.search:
        print(f"Searching for companies matching '{args.search}'...")
        companies = search_companies(args.search, limit=10)
        
        if not companies:
            print("No companies found.")
            return
        
        print(f"\nFound {len(companies)} companies:")
        print("-" * 60)
        for i, company in enumerate(companies, 1):
            print(f"{i:2}. {company.get('name', 'Unknown')}")
            print(f"    Ticker: {company.get('ticker', 'Unknown')}")
            print(f"    CIK: {company.get('cik', 'Unknown')}")
            print()
        
        print("Use --cik, --ticker, or --company with one of the above CIKs to download filings.")
        return
    
    # Validate that at least one input method is provided
    if not any([args.cik, args.ticker, args.company, args.search]):
        print("Error: Please provide --cik, --ticker, --company, or --search")
        parser.print_help()
        return
    
    # Determine CIK, company name, and ticker
    cik = None
    company_name = None
    ticker = None
    
    if args.cik:
        cik = args.cik.zfill(10)  # Ensure 10-digit format
        if args.verbose:
            print(f"Using provided CIK: {cik}")
        company_name = get_company_name(cik)
        
    elif args.ticker:
        if args.verbose:
            print(f"Looking up CIK for ticker: {args.ticker}")
        cik = get_cik_by_name_or_ticker(args.ticker)
        if not cik:
            print(f"Error: Could not find CIK for ticker '{args.ticker}'")
            print("Try using --search to find the correct ticker or use --cik directly.")
            return
        company_name = get_company_name(cik)
        ticker = args.ticker.upper()
        
    elif args.company:
        if args.verbose:
            print(f"Looking up CIK for company: {args.company}")
        cik = get_cik_by_name_or_ticker(args.company)
        if not cik:
            print(f"Error: Could not find CIK for company '{args.company}'")
            print("Try using --search to find the correct company name or use --cik directly.")
            return
        company_name = args.company
    
    if not cik:
        print("Error: Could not determine CIK. Please check your input.")
        return
    
    # Display company information
    print(f"Extracting {args.max_filings} {', '.join(args.forms)} filings for {company_name}...")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Execute scraping
    try:
        saved_files = execute_scraping(
            cik=cik,
            company_name=company_name,
            form_types=args.forms,
            max_filings=args.max_filings,
            output_dir=args.output_dir,
            ticker=ticker
        )
        
        print(f"\nCompleted! Downloaded {len(saved_files)} files to {args.output_dir}")
            
    except Exception as e:
        print(f"Error during scraping: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
