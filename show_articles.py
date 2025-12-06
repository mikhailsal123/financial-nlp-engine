#!/usr/bin/env python3
"""
News Article Viewer
Display downloaded news articles with metadata and full content for verification.
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))


def view_article(ticker: str, article_idx: Optional[int] = None):
    """
    View downloaded articles for a ticker.
    
    Args:
        ticker: Stock ticker (e.g., 'NVDA')
        article_idx: Optional article index (0-based) to view specific article
    """
    articles_dir = Path("data/output/news_articles") / ticker
    
    if not articles_dir.exists():
        print(f"✗ No articles found for {ticker}")
        print(f"  Path: {articles_dir}")
        return
    
    # Get all article files, sorted by filename
    article_files = sorted(articles_dir.glob("*.json"))
    
    if not article_files:
        print(f"✗ No articles found in {articles_dir}")
        return
    
    print(f"\n{'='*100}")
    print(f"DOWNLOADED NEWS ARTICLES FOR {ticker}")
    print(f"{'='*100}")
    print(f"Total articles: {len(article_files)}\n")
    
    if article_idx is not None:
        # View specific article
        if article_idx < 0 or article_idx >= len(article_files):
            print(f"✗ Invalid article index. Valid range: 0-{len(article_files)-1}")
            return
        
        filepath = article_files[article_idx]
        display_article(filepath, article_idx)
        
    else:
        # List all articles
        for idx, filepath in enumerate(article_files):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    meta = data.get("metadata", {})
                    print(f"[{idx:2d}] {meta.get('headline', 'N/A')[:80]}")
                    print(f"     Source: {meta.get('source', 'N/A')} | Published: {meta.get('published_at', 'N/A')}")
                    print()
            except Exception as e:
                print(f"[{idx:2d}] Error reading: {e}\n")
        
        # Show help for viewing specific articles
        print(f"\nTo view full content of an article, run:")
        print(f"  python show_articles.py {ticker} --idx <number>")
        print(f"\nExample: python show_articles.py {ticker} --idx 0")


def display_article(filepath: Path, idx: int):
    """Display full content of a single article"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            meta = data.get("metadata", {})
            content = data.get("content", "")
            
            print(f"\n{'='*100}")
            print(f"ARTICLE #{idx}")
            print(f"{'='*100}")
            print(f"\nHeadline: {meta.get('headline', 'N/A')}")
            print(f"Source: {meta.get('source', 'N/A')}")
            print(f"URL: {meta.get('url', 'N/A')}")
            print(f"Published: {meta.get('published_at', 'N/A')}")
            print(f"Downloaded: {meta.get('downloaded_at', 'N/A')}")
            print(f"Sentiment: {meta.get('sentiment', 'N/A')}")
            print(f"Category: {meta.get('category', 'N/A')}")
            print(f"\n{'-'*100}")
            print(f"CONTENT (first 3000 chars):")
            print(f"{'-'*100}\n")
            
            # Show first 3000 characters of content (usually HTML)
            preview = content[:3000] if content else "[No content captured]"
            print(preview)
            
            if len(content) > 3000:
                print(f"\n... ({len(content) - 3000} more characters)")
            
            print(f"\n{'='*100}")
            print(f"Full HTML saved in: {filepath}")
            print(f"(Total content size: {len(content)} characters)")
            print(f"{'='*100}\n")
            
    except Exception as e:
        print(f"✗ Error reading article: {e}")


def list_tickers():
    """List all tickers with downloaded articles"""
    articles_root = Path("data/output/news_articles")
    if not articles_root.exists():
        print("✗ No articles directory found")
        return
    
    tickers = [d.name for d in articles_root.iterdir() if d.is_dir()]
    if not tickers:
        print("✗ No tickers with downloaded articles")
        return
    
    print("\nTickers with downloaded articles:")
    for ticker in sorted(tickers):
        article_count = len(list((articles_root / ticker).glob("*.json")))
        print(f"  • {ticker}: {article_count} articles")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="View downloaded news articles for stock analysis verification"
    )
    parser.add_argument(
        "ticker",
        nargs="?",
        help="Stock ticker (e.g., NVDA, MSFT)"
    )
    parser.add_argument(
        "--idx",
        type=int,
        help="Article index (0-based) to view full content"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all tickers with downloaded articles"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_tickers()
    elif args.ticker:
        view_article(args.ticker.upper(), args.idx)
    else:
        parser.print_help()
        print("\n\nAvailable tickers:")
        list_tickers()
