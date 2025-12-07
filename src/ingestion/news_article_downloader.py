"""
News Article Downloader
Downloads full text of news articles from URLs for source verification and archival.
Saves articles locally with metadata for traceability.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests
from pathlib import Path

logger = logging.getLogger(__name__)


class NewsArticleDownloader:
    """
    Downloads and archives news articles from Finnhub news feed.
    Stores articles locally with metadata for verification and analysis.
    """

    def __init__(self, output_dir: str = "data/output/news_articles"):
        """
        Initialize the downloader.
        
        Args:
            output_dir: Directory to save downloaded articles (organized by ticker)
        """
        self.output_dir = output_dir
        self._ensure_directories_exist()

    def _ensure_directories_exist(self) -> None:
        """Create output directory if it doesn't exist"""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def download_articles(self, ticker: str, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Download full text of news articles from the provided news items.
        
        Args:
            ticker: Stock ticker symbol
            news_items: List of news item dicts from Finnhub with 'url' and 'headline' keys
            
        Returns:
            Dict with download summary (successful, failed, saved_files)
        """
        results = {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "total_articles": len(news_items),
            "successful": 0,
            "failed": 0,
            "saved_files": [],
            "errors": []
        }

        # Create ticker-specific directory
        ticker_dir = Path(self.output_dir) / ticker
        ticker_dir.mkdir(parents=True, exist_ok=True)

        for idx, item in enumerate(news_items):
            try:
                url = item.get("url")
                headline = item.get("headline", "Unknown")
                source = item.get("source", "unknown")
                published_at = item.get("datetime", 0)

                if not url:
                    logger.warning(f"Skipping article {idx}: no URL")
                    results["failed"] += 1
                    results["errors"].append({"index": idx, "error": "No URL provided"})
                    continue

                # Download article
                article_content = self._fetch_article_content(url)
                if not article_content:
                    results["failed"] += 1
                    results["errors"].append({
                        "index": idx,
                        "headline": headline,
                        "url": url,
                        "error": "Failed to fetch content"
                    })
                    continue

                # Generate filename based on timestamp and source
                filename = self._generate_filename(source, published_at, idx)
                filepath = ticker_dir / filename

                # Save article with metadata
                article_data = {
                    "metadata": {
                        "ticker": ticker,
                        "headline": headline,
                        "url": url,
                        "source": source,
                        "published_at": published_at,
                        "downloaded_at": datetime.now().isoformat(),
                        "sentiment": item.get("sentiment"),
                        "category": item.get("category")
                    },
                    "content": article_content
                }

                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(article_data, f, indent=2, ensure_ascii=False)

                results["successful"] += 1
                results["saved_files"].append({
                    "filename": filename,
                    "path": str(filepath),
                    "headline": headline,
                    "source": source,
                    "url": url
                })

                logger.info(f"Saved article {idx+1}/{len(news_items)}: {headline[:60]}...")

            except Exception as e:
                logger.error(f"Error processing article {idx}: {e}")
                results["failed"] += 1
                results["errors"].append({
                    "index": idx,
                    "error": str(e)
                })

        return results

    def _fetch_article_content(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Fetch full article content from URL using requests.
        
        Args:
            url: Article URL
            timeout: Request timeout in seconds
            
        Returns:
            HTML/text content of article, or None if fetch failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def _generate_filename(self, source: str, timestamp: int, index: int) -> str:
        """
        Generate a descriptive filename for the article.
        
        Args:
            source: News source (e.g., 'Reuters', 'Yahoo', 'Bloomberg')
            timestamp: Unix timestamp of article publication
            index: Index in batch (for uniqueness)
            
        Returns:
            Filename in format: YYYYMMDD_HHmmss_source_idx.json
        """
        try:
            dt = datetime.fromtimestamp(timestamp)
            datestr = dt.strftime("%Y%m%d_%H%M%S")
        except (ValueError, TypeError):
            datestr = datetime.now().strftime("%Y%m%d_%H%M%S")

        source_clean = source.replace(" ", "").replace("/", "").lower()[:20]
        return f"{datestr}_{source_clean}_{index:03d}.json"

    def get_saved_articles_summary(self, ticker: str) -> Dict[str, Any]:
        """
        Get a summary of all saved articles for a ticker.
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Dict with list of saved articles and metadata
        """
        ticker_dir = Path(self.output_dir) / ticker
        if not ticker_dir.exists():
            return {
                "ticker": ticker,
                "articles_found": 0,
                "articles": []
            }

        articles = []
        for filepath in sorted(ticker_dir.glob("*.json")):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    articles.append({
                        "filename": filepath.name,
                        "headline": data.get("metadata", {}).get("headline"),
                        "source": data.get("metadata", {}).get("source"),
                        "url": data.get("metadata", {}).get("url"),
                        "downloaded_at": data.get("metadata", {}).get("downloaded_at")
                    })
            except Exception as e:
                logger.warning(f"Could not read {filepath}: {e}")

        return {
            "ticker": ticker,
            "articles_found": len(articles),
            "articles": articles
        }

    def cleanup_old_articles(self, ticker: str, keep_days: int = 30) -> Dict[str, Any]:
        """
        Remove articles older than keep_days.
        
        Args:
            ticker: Stock ticker
            keep_days: Number of days to keep articles
            
        Returns:
            Dict with cleanup summary
        """
        from datetime import timedelta

        ticker_dir = Path(self.output_dir) / ticker
        if not ticker_dir.exists():
            return {"ticker": ticker, "removed": 0, "kept": 0}

        cutoff_date = datetime.now() - timedelta(days=keep_days)
        removed = 0
        kept = 0

        for filepath in ticker_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    downloaded_at_str = data.get("metadata", {}).get("downloaded_at")
                    if downloaded_at_str:
                        downloaded_at = datetime.fromisoformat(downloaded_at_str)
                        if downloaded_at < cutoff_date:
                            filepath.unlink()
                            removed += 1
                        else:
                            kept += 1
            except Exception as e:
                logger.warning(f"Error processing {filepath}: {e}")

        return {
            "ticker": ticker,
            "cutoff_date": cutoff_date.isoformat(),
            "removed": removed,
            "kept": kept
        }
