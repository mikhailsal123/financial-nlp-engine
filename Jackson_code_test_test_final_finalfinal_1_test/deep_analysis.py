#!/usr/bin/env python3
"""
Comprehensive Deep Financial Analysis Tool
Pulls from all 4 APIs (Alpha Vantage, Finnhub, FRED, Yahoo Finance)
and generates in-depth company outlook reports

Usage:
    python deep_analysis.py --ticker NVDA
    python deep_analysis.py --ticker AAPL --lookback 180
"""

import argparse
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
load_dotenv()

# Configure stdout for UTF-8
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.analysis.comprehensive_aggregator import aggregate_company_data
from src.analysis.deep_analysis_engine import generate_deep_analysis_report
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def format_report_for_display(report: Dict[str, Any], aggregated_data: Dict[str, Any]) -> str:
    """Format the deep analysis report into a readable text report"""
    
    lines = []
    lines.append("=" * 100)
    lines.append("COMPREHENSIVE FINANCIAL ANALYSIS REPORT")
    lines.append("=" * 100)
    lines.append("")

    # Header
    ticker = report.get("ticker", "N/A")
    generated_at = report.get("generated_at", "N/A")
    lines.append(f"Ticker: {ticker}")
    lines.append(f"Generated: {generated_at}")
    lines.append("")

    sections = report.get("sections", {})

    # Executive Summary
    exec_summary = sections.get("executive_summary", {})
    lines.append("┌" + "─" * 98 + "┐")
    lines.append("│ EXECUTIVE SUMMARY" + " " * 81 + "│")
    lines.append("└" + "─" * 98 + "┘")
    lines.append(f"Company: {exec_summary.get('company_name', 'N/A')}")
    lines.append(f"Industry: {exec_summary.get('industry', 'N/A')}")
    lines.append(f"Current Position: {exec_summary.get('current_position', 'N/A').upper()}")
    lines.append(f"Assessment: {exec_summary.get('headline', 'N/A')}")
    lines.append("")

    # Key Metrics
    metrics = exec_summary.get("key_metrics", {})
    lines.append("Key Financial Metrics:")
    for key, value in metrics.items():
        if value != "N/A":
            lines.append(f"  • {key.replace('_', ' ').title()}: {value}")
    lines.append("")

    # Market Position
    market = sections.get("market_position", {})
    lines.append("┌" + "─" * 98 + "┐")
    lines.append("│ MARKET POSITION & VALUATION" + " " * 68 + "│")
    lines.append("└" + "─" * 98 + "┘")
    if market.get("valuation"):
        lines.append(f"Valuation: {market['valuation']}")
    if market.get("momentum"):
        lines.append(f"Price Momentum: {market['momentum']}")
    if market.get("relative_strength"):
        lines.append(f"Relative Strength: {market['relative_strength']}")
    lines.append("")

    # Financial Health
    health = sections.get("financial_health", {})
    lines.append("┌" + "─" * 98 + "┐")
    lines.append("│ FINANCIAL HEALTH & STABILITY" + " " * 68 + "│")
    lines.append("└" + "─" * 98 + "┘")
    if health.get("profitability"):
        lines.append(f"Profitability: {health['profitability']}")
    if health.get("leverage"):
        lines.append(f"Leverage: {health['leverage']}")
    lines.append("")

    # Growth Analysis
    growth = sections.get("growth_trajectory", {})
    lines.append("┌" + "─" * 98 + "┐")
    lines.append("│ GROWTH TRAJECTORY" + " " * 79 + "│")
    lines.append("└" + "─" * 98 + "┘")
    if growth.get("eps_trend"):
        lines.append(f"EPS Trend: {growth['eps_trend']}")
    lines.append("")

    # Risk Assessment
    risks = sections.get("risk_assessment", {})
    lines.append("┌" + "─" * 98 + "┐")
    lines.append("│ RISK ASSESSMENT" + " " * 81 + "│")
    lines.append("└" + "─" * 98 + "┘")
    high_risks = risks.get("high_risk_factors", [])
    med_risks = risks.get("medium_risk_factors", [])
    
    if high_risks:
        lines.append("HIGH RISK FACTORS:")
        for risk in high_risks:
            lines.append(f"  [!] {risk}")
    
    if med_risks:
        lines.append("MEDIUM RISK FACTORS:")
        for risk in med_risks:
            lines.append(f"  [*] {risk}")
    
    if not high_risks and not med_risks:
        lines.append("No significant risk factors identified")
    lines.append("")

    # News Sentiment Analysis
    news_sentiment = sections.get("news_sentiment", {})
    if news_sentiment:
        lines.append("┌" + "─" * 98 + "┐")
        lines.append("│ NEWS SENTIMENT ANALYSIS (FinBERT)" + " " * 64 + "│")
        lines.append("└" + "─" * 98 + "┘")
        if news_sentiment.get("finbert_sentiment"):
            lines.append(f"Overall: {news_sentiment['finbert_sentiment']}")
        
        top_news = news_sentiment.get("top_news_items", [])
        if top_news:
            lines.append("\nRecent News Headlines:")
            for i, news in enumerate(top_news[:5], 1):
                sentiment = news.get("finbert_sentiment", "N/A").upper()
                confidence = news.get("confidence", 0)
                headline = news.get("headline", "")[:70]
                lines.append(f"  {i}. [{sentiment} {confidence:.0%}] {headline}")
        lines.append("")

    # Positives / Negatives / Neutral synthesis
    pnn = sections.get("pos_neg_neutral", {})
    if pnn:
        lines.append("┌" + "─" * 98 + "┐")
        lines.append("│ POSITIVES / NEGATIVES / NEUTRAL (SYNTHESIS)" + " " * 41 + "│")
        lines.append("└" + "─" * 98 + "┘")

        pos = pnn.get("positives", [])
        neg = pnn.get("negatives", [])
        neu = pnn.get("neutral", [])

        if pos:
            lines.append("Positives:")
            for item in pos[:5]:
                text = item.get("text", "")[:180]
                source = item.get("source", "")
                conf = item.get("confidence", 0)
                lines.append(f"  • {text} ({source}, {conf:.0%})")
            lines.append("")

        if neg:
            lines.append("Negatives:")
            for item in neg[:5]:
                text = item.get("text", "")[:180]
                source = item.get("source", "")
                conf = item.get("confidence", 0)
                lines.append(f"  • {text} ({source}, {conf:.0%})")
            lines.append("")

        if neu:
            lines.append("Neutral / Watchlist:")
            for item in neu[:5]:
                text = item.get("text", "")[:180]
                source = item.get("source", "")
                conf = item.get("confidence", 0)
                lines.append(f"  • {text} ({source}, {conf:.0%})")
            lines.append("")

    # Peer comparison
    peer_comp = sections.get("peer_comparison", {})
    if peer_comp:
        lines.append("┌" + "─" * 98 + "┐")
        lines.append("│ PEER COMPARISON" + " " * 84 + "│")
        lines.append("└" + "─" * 98 + "┘")

        summary = peer_comp.get("summary", {})
        if summary:
            lines.append("Peer Summary:")
            for k, v in summary.items():
                lines.append(f"  • {k.replace('_', ' ').title()}: {v}")
            lines.append("")

        by_mc = peer_comp.get("by_market_cap", [])
        if by_mc:
            lines.append("Peers by Market Cap (top 5):")
            for p in by_mc[:5]:
                mc = p.get('market_cap')
                # human readable format
                def hr(x):
                    try:
                        if x is None:
                            return 'N/A'
                        x = float(x)
                        if x >= 1e12:
                            return f"${x/1e12:.2f}T"
                        if x >= 1e9:
                            return f"${x/1e9:.2f}B"
                        if x >= 1e6:
                            return f"${x/1e6:.2f}M"
                        return f"${x:.2f}"
                    except:
                        return str(x)

                lines.append(f"  • {p.get('ticker')}: {hr(mc)}")
            lines.append("")

        by_pe = peer_comp.get("by_pe", [])
        if by_pe:
            lines.append("Peers by P/E (low to high):")
            for p in by_pe[:5]:
                lines.append(f"  • {p.get('ticker')}: {p.get('pe_ratio')}")
            lines.append("")

    # Macroeconomic Impact
    macro = sections.get("macro_impact", {})
    lines.append("┌" + "─" * 98 + "┐")
    lines.append("│ MACROECONOMIC CONTEXT" + " " * 76 + "│")
    lines.append("└" + "─" * 98 + "┘")
    if macro.get("economic_environment"):
        lines.append(f"Environment: {macro['economic_environment']}")
    
    indicators = macro.get("relevant_indicators", {})
    if indicators:
        lines.append("Economic Indicators:")
        for key, val in indicators.items():
            if isinstance(val, dict) and "value" in val:
                lines.append(f"  • {key}: {val['value']}")
    lines.append("")

    # Investment Thesis
    thesis = sections.get("investment_thesis", {})
    lines.append("┌" + "─" * 98 + "┐")
    lines.append("│ INVESTMENT THESIS" + " " * 79 + "│")
    lines.append("└" + "─" * 98 + "┘")
    if thesis.get("bull_case"):
        lines.append(f"BULL CASE: {thesis['bull_case']}")
    if thesis.get("bear_case"):
        lines.append(f"BEAR CASE: {thesis['bear_case']}")
    if thesis.get("conviction_level"):
        lines.append(f"Conviction Level: {thesis['conviction_level']}")
    lines.append("")

    # Forward Outlook
    outlook = sections.get("forward_outlook", {})
    lines.append("┌" + "─" * 98 + "┐")
    lines.append("│ FORWARD OUTLOOK" + " " * 81 + "│")
    lines.append("└" + "─" * 98 + "┘")
    if outlook.get("price_target_12m"):
        lines.append(f"12-Month Price Target: {outlook['price_target_12m']}")
    if outlook.get("upside_downside"):
        lines.append(f"Upside/Downside: {outlook['upside_downside']}")
    
    catalysts = outlook.get("key_catalysts", [])
    if catalysts:
        lines.append("Key Catalysts:")
        for cat in catalysts:
            lines.append(f"  • {cat}")
    
    if outlook.get("outlook_summary"):
        lines.append(f"Summary: {outlook['outlook_summary']}")
    lines.append("")

    # Data Quality
    errors = aggregated_data.get("errors", [])
    if errors:
        lines.append("┌" + "─" * 98 + "┐")
        lines.append("│ DATA QUALITY NOTES" + " " * 78 + "│")
        lines.append("└" + "─" * 98 + "┘")
        for error in errors:
            lines.append(f"  • {error}")
        lines.append("")

    lines.append("=" * 100)
    
    return "\n".join(lines)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Comprehensive Deep Financial Analysis - Multi-API Integration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deep_analysis.py --ticker NVDA
  python deep_analysis.py --ticker AAPL --lookback 180 --output reports/
        """
    )
    
    parser.add_argument('--ticker', required=True, help='Stock ticker symbol (e.g., NVDA, AAPL)')
    parser.add_argument('--lookback', type=int, default=90, help='Days of historical data to analyze (default: 90)')
    parser.add_argument('--output', default='data/output/deep_analysis', help='Output directory for reports')
    parser.add_argument('--no-save', action='store_true', help='Do not save reports to disk')
    
    args = parser.parse_args()
    
    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE DEEP FINANCIAL ANALYSIS")
    print(f"{'='*80}\n")
    
    print(f"Ticker: {args.ticker}")
    print(f"Lookback: {args.lookback} days\n")
    
    # Aggregate data from all APIs
    print("Aggregating data from all financial APIs...")
    print("  • Alpha Vantage (prices & fundamentals)")
    print("  • Finnhub (company data & earnings)")
    print("  • FRED (macroeconomic indicators)")
    print("  • Yahoo Finance (market data)")
    print("")
    
    try:
        aggregated_data = aggregate_company_data(args.ticker, args.lookback)
        print("✓ Data aggregation complete\n")
    except Exception as e:
        print(f"✗ Error aggregating data: {e}")
        sys.exit(1)
    
    # Generate deep analysis
    print("Generating comprehensive analysis...")
    try:
        report = generate_deep_analysis_report(args.ticker, aggregated_data)
        print("✓ Analysis complete\n")
    except Exception as e:
        print(f"✗ Error generating analysis: {e}")
        sys.exit(1)
    
    # Format and display report
    formatted_report = format_report_for_display(report, aggregated_data)
    print(formatted_report)
    
    # Save if requested
    if not args.no_save:
        print("\nSaving reports...")
        try:
            os.makedirs(args.output, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Save formatted report
            report_file = os.path.join(args.output, f"{args.ticker}_deep_analysis_{timestamp}.txt")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(formatted_report)
            print(f"✓ Report saved: {report_file}")
            
            # Save raw JSON data
            json_file = os.path.join(args.output, f"{args.ticker}_analysis_data_{timestamp}.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                # Combine report and aggregated data for JSON
                output = {
                    "report": report,
                    "aggregated_data": aggregated_data,
                }
                json.dump(output, f, indent=2, default=str)
            print(f"✓ JSON data saved: {json_file}")
            
            # Show article download info
            article_summary = aggregated_data.get("news_sentiment", {}).get("article_download_summary", {})
            if article_summary and article_summary.get("successful", 0) > 0:
                articles_dir = f"data/output/news_articles/{args.ticker}"
                print(f"✓ Downloaded {article_summary['successful']} articles")
                print(f"  → Articles saved to: {articles_dir}/")
                print(f"  → Each article has headline, source, URL, and content for verification")
            
        except Exception as e:
            print(f"✗ Error saving reports: {e}")
    
    print("\nAnalysis complete!")


if __name__ == '__main__':
    main()
