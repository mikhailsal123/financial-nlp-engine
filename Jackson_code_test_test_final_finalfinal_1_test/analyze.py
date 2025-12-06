#!/usr/bin/env python3
"""
Main Entry Point for Financial NLP Engine
Unified interface: python analyze.py --ticker NVDA

This is the single command you use to get complete analysis:
- Sentiment analysis of earnings reports
- Financial metric extraction
- Market data integration
- Trading signal generation
"""

import argparse
import sys
import os
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

# Configure stdout for UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.append(os.path.dirname(__file__))

from src.orchestration.unified_pipeline import UnifiedPipeline


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Financial NLP Engine - Complete Stock Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single company
  python analyze.py --ticker NVDA
  
  # Analyze with custom parameters
  python analyze.py --ticker AAPL --max-filings 5 --lookback 180
  
  # Output to specific directory
  python analyze.py --ticker MSFT --output data/my_analysis
        """
    )
    
    parser.add_argument(
        '--ticker',
        required=True,
        help='Stock ticker symbol (e.g., NVDA, AAPL, MSFT)'
    )
    
    parser.add_argument(
        '--max-filings',
        type=int,
        default=3,
        help='Maximum number of SEC filings to analyze (default: 3)'
    )
    
    parser.add_argument(
        '--lookback',
        type=int,
        default=90,
        help='Days of historical stock data to fetch (default: 90)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output directory for results (default: data/output/integrated_analysis)'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save results to disk'
    )
    
    args = parser.parse_args()
    
    # Initialize pipeline
    print("Initializing Financial NLP Engine...")
    pipeline = UnifiedPipeline()
    
    # Run analysis
    print(f"\nAnalyzing {args.ticker}...")
    print("-" * 80)
    
    analysis = pipeline.analyze_company(
        ticker=args.ticker,
        max_filings=args.max_filings,
        lookback_days=args.lookback,
    )
    
    # Display results
    if analysis['status'] == 'success':
        print(analysis['summary'])
        
        # Save if requested
        if not args.no_save:
            print("\nSaving analysis...")
            json_file, summary_file = pipeline.save_analysis(analysis, args.output)
            print(f"✅ Analysis saved successfully")
    else:
        print(f"❌ Error: {analysis.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == '__main__':
    main()
