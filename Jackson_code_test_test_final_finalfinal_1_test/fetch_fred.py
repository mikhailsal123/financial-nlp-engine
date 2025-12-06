#!/usr/bin/env python3
"""
Command line tool for downloading FRED time series with automatic 'change' and
'good/bad/neutral' labels.
"""

import argparse
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from src.fred_client import download_series, get_series_info
from src.fred_lookup import search_series


def main():
    parser = argparse.ArgumentParser(
        description='Download FRED time series with change + label metrics.',  # >>> UPDATED
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fetch_fred.py --search "GDP"
  python fetch_fred.py --series-id UNRATE
        """
    )

    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument('--search', help='Search for FRED series')

    parser.add_argument('--start-date', help='Start date (YYYY-MM-DD)', default=None)
    parser.add_argument('--end-date', help='End date (YYYY-MM-DD)', default=None)
    parser.add_argument('--frequency', help='Frequency (m, q, a)', default=None)

    parser.add_argument('--output-dir', default='data/raw/fred',
                        help='Output directory (default: data/raw/fred)')
    parser.add_argument('--format', choices=['csv', 'json'], default='csv',
                        help='Output format (default: csv)')
    parser.add_argument('--series-id', help='FRED series ID (e.g., GDP, UNRATE)')
    parser.add_argument('--max-rows', type=int, default=None,
                        help='Maximum number of observations')

    args = parser.parse_args()

    # Search mode
    if args.search:
        print(f"Searching FRED for '{args.search}'...")
        results = search_series(args.search, limit=10)

        if not results:
            print("No results found.")
            return

        print("\nFound series:")
        print("-" * 70)
        for i, s in enumerate(results, 1):
            print(f"{i}. {s.get('id', 'Unknown')}: {s.get('title', 'No title')}")
        return

    if not args.series_id:
        print("Error: must provide --series-id or --search")
        parser.print_help()
        return

    series_id = args.series_id.upper()

    try:
        info = get_series_info(series_id)
        title = info.get('title', series_id)
    except Exception as e:
        print(f"Warning: could not fetch metadata: {e}")
        title = series_id

    print(f"Downloading {series_id} - {title}...")
    os.makedirs(args.output_dir, exist_ok=True)

    try:
        out = download_series(
            series_id=series_id,
            start_date=args.start_date,
            end_date=args.end_date,
            frequency=args.frequency,
            output_dir=args.output_dir,
            fmt=args.format,
            max_rows=args.max_rows
        )

        print(f"Saved file with change + label metrics → {out}")  # >>> UPDATED
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()