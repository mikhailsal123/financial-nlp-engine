#!/usr/bin/env python3
"""
Command-line tool for scraping SEC EDGAR filings
"""

import argparse
from src.ingestion.sec_scraper import execute_scraping, get_company_name


def main():
    parser = argparse.ArgumentParser(description='Scrape SEC EDGAR filings')
    parser.add_argument('--cik', required=True, help='Company CIK')
    parser.add_argument('--company', default=None, help='Company name (optional, will auto-lookup if not provided)')
    parser.add_argument('--forms', nargs='+', default=['10-Q', '10-K'], 
                       help='Form types to scrape (default: 10-Q 10-K)')
    parser.add_argument('--max-filings', type=int, default=5, 
                       help='Maximum number of filings to download (default: 5)')
    parser.add_argument('--output-dir', default='data/processed/earnings_reports',
                       help='Output directory (default: data/processed/earnings_reports)')
    
    args = parser.parse_args()
    
    # Get company name if not provided
    if not args.company:
        print(f"Looking up company name for CIK {args.cik}...")
        company_name = get_company_name(args.cik)
        print(f"Found company: {company_name}")
    else:
        company_name = args.company
    
    # Execute scraping
    saved_files = execute_scraping(
        cik=args.cik,
        company_name=company_name,
        form_types=args.forms,
        max_filings=args.max_filings,
        output_dir=args.output_dir
    )
    
    print(f"\nCompleted! Downloaded {len(saved_files)} filings to {args.output_dir}")


if __name__ == "__main__":
    main()
