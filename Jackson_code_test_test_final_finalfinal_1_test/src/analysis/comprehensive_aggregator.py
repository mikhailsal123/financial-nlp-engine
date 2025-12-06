"""
Comprehensive Multi-API Data Aggregator for Deep Financial Analysis
Pulls from Alpha Vantage, Finnhub, FRED, and Yahoo Finance to create
a rich contextual dataset for in-depth company outlook analysis
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.parsing.section_extractor import SectionExtractor
from src.ingestion.sec_scraper import SECScraper
from src.ingestion.company_lookup import get_cik_by_name_or_ticker
from src.ingestion.news_article_downloader import NewsArticleDownloader

logger = logging.getLogger(__name__)


class ComprehensiveDataAggregator:
    """
    Aggregates data from all 4 financial APIs into a unified, rich dataset
    suitable for deep analysis and FinBERT processing
    """

    def __init__(self):
        """Initialize all API clients"""
        self.alpha_vantage = None
        self.finnhub = None
        self.fred = None
        self.yahoo = None
        self.article_downloader = NewsArticleDownloader()
        self._init_clients()

    def _init_clients(self):
        """Initialize API clients safely"""
        try:
            from alpha_vantage_client import AlphaVantageClient
            self.alpha_vantage = AlphaVantageClient()
        except Exception as e:
            logger.warning(f"Alpha Vantage client init failed: {e}")

        try:
            from finnhub_client import FinnhubClient
            self.finnhub = FinnhubClient()
        except Exception as e:
            logger.warning(f"Finnhub client init failed: {e}")

        try:
            from src.fred_client import download_series
            self.fred = download_series
        except Exception as e:
            logger.warning(f"FRED client init failed: {e}")

        try:
            import yfinance as yf
            self.yahoo = yf
        except Exception as e:
            logger.warning(f"Yahoo Finance init failed: {e}")

    def aggregate_comprehensive_data(self, ticker: str, lookback_days: int = 90) -> Dict[str, Any]:
        """
        Aggregate ALL available data from all APIs in parallel.
        
        This creates a rich context document that includes:
        - Current market position
        - Price momentum & technicals
        - Company fundamentals
        - Recent news & sentiment indicators
        - Earnings history & guidance
        - Macroeconomic context
        - Industry peers comparison
        
        Returns a dict with all collected data organized by category.
        """

        aggregated = {
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "market_data": {},
            "fundamentals": {},
            "company_profile": {},
            "news_sentiment": {},
            "earnings_analysis": {},
            "macroeconomic_context": {},
            "peer_analysis": {},
            "technical_analysis": {},
            "errors": []
        }

        # Use thread pool to fetch all data in parallel
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                "market": executor.submit(self._fetch_market_data, ticker),
                "fundamentals": executor.submit(self._fetch_fundamentals, ticker),
                "profile": executor.submit(self._fetch_company_profile, ticker),
                "news": executor.submit(self._fetch_news_sentiment, ticker, lookback_days),
                "earnings": executor.submit(self._fetch_earnings_analysis, ticker),
                "macro": executor.submit(self._fetch_macroeconomic_context),
                "filings": executor.submit(self._fetch_filings, ticker, 2),
                "peers": executor.submit(self._fetch_peer_analysis, ticker),
                "technicals": executor.submit(self._fetch_technical_analysis, ticker, lookback_days),
            }

            for key, future in futures.items():
                try:
                    result = future.result(timeout=30)
                    if result:
                        if key == "market":
                            aggregated["market_data"] = result
                        elif key == "fundamentals":
                            aggregated["fundamentals"] = result
                        elif key == "profile":
                            aggregated["company_profile"] = result
                        elif key == "news":
                            aggregated["news_sentiment"] = result
                        elif key == "earnings":
                            aggregated["earnings_analysis"] = result
                        elif key == "macro":
                            aggregated["macroeconomic_context"] = result
                        elif key == "filings":
                            aggregated["filings"] = result
                        elif key == "peers":
                            aggregated["peer_analysis"] = result
                            # Normalize peer metrics for downstream comparison
                            try:
                                normalized = self._normalize_peer_metrics(result.get("peer_metrics", {}))
                                aggregated["peer_analysis"]["peer_metrics_normalized"] = normalized
                            except Exception as e:
                                logger.debug(f"Failed to normalize peer metrics: {e}")
                        elif key == "technicals":
                            aggregated["technical_analysis"] = result
                except Exception as e:
                    logger.error(f"Error fetching {key}: {e}")
                    aggregated["errors"].append(f"{key}: {str(e)}")

        # Post-checks: if peers not fetched, add clear guidance
        try:
            peer_info = aggregated.get('peer_analysis', {})
            if not peer_info or not peer_info.get('peer_tickers'):
                aggregated['errors'].append('peers: missing or empty - check Finnhub API key/plan or rate limits')
        except Exception:
            pass

        return aggregated

    def _fetch_filings(self, ticker: str, max_filings: int = 2) -> Dict[str, Any]:
        """Fetch recent SEC filings and extract priority sections"""
        result: Dict[str, Any] = {"raw": [], "sections": {}}

        try:
            cik = get_cik_by_name_or_ticker(ticker)
            if not cik:
                return result

            scraper = SECScraper()
            extractor = SectionExtractor()

            filings = scraper.get_filings_api(cik, form_type='10-Q', max_filings=max_filings)
            if not filings:
                filings = scraper.get_filings(cik, form_type='10-Q', max_filings=max_filings)

            for filing in filings:
                filing_url = filing.get('filing_url')
                if not filing_url:
                    continue

                docs = scraper.get_filing_documents(filing_url)
                if not docs:
                    continue

                doc = docs[0]
                try:
                    response = scraper.session.get(doc.get('url'))
                    if response.status_code == 200:
                        text = scraper.extract_text_from_html(response.text)
                        result['raw'].append({'url': doc.get('url'), 'text': text, 'date': filing.get('filing_date')})

                        sections = extractor.extract_sections(text)
                        for name, section in sections.items():
                            # Keep longest section if multiple filings
                            if name not in result['sections'] or len(section.content) > len(result['sections'][name]):
                                result['sections'][name] = section.content
                except Exception as e:
                    logger.debug(f"Failed to fetch filing document {doc.get('url')}: {e}")

        except Exception as e:
            logger.debug(f"Filing fetch failed for {ticker}: {e}")

        return result
        
        # Fallback: look for local files under data/raw/earnings_reports matching ticker
        try:
            local_dir = os.path.join('data', 'raw', 'earnings_reports')
            if os.path.exists(local_dir):
                for fname in os.listdir(local_dir):
                    if fname.upper().startswith(ticker.upper()) and fname.lower().endswith('.txt'):
                        path = os.path.join(local_dir, fname)
                        try:
                            with open(path, 'r', encoding='utf-8') as f:
                                text = f.read()
                            result['raw'].append({'url': f'local:{fname}', 'text': text, 'date': None})
                            sections = SectionExtractor().extract_sections(text)
                            for name, section in sections.items():
                                if name not in result['sections'] or len(section.content) > len(result['sections'][name]):
                                    result['sections'][name] = section.content
                        except Exception:
                            continue
        except Exception:
            pass

        return result

    def _normalize_peer_metrics(self, peer_metrics: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Normalize peer metrics to consistent numeric types when possible."""
        def parse_number(val):
            if val is None:
                return None
            try:
                if isinstance(val, (int, float)):
                    return float(val)
                s = str(val)
                # Remove common formatting
                s = s.replace('$', '').replace(',', '').replace('%', '').strip()
                if s == '' or s.lower() in ('n/a', 'none'):
                    return None
                return float(s)
            except Exception:
                return None

        normalized: Dict[str, Dict[str, Any]] = {}
        for peer, metrics in (peer_metrics or {}).items():
            out: Dict[str, Any] = {}
            out['market_cap'] = parse_number(metrics.get('market_cap'))
            out['pe_ratio'] = parse_number(metrics.get('pe_ratio'))
            out['eps'] = parse_number(metrics.get('eps'))
            out['revenue'] = parse_number(metrics.get('revenue'))
            out['price_to_book'] = parse_number(metrics.get('price_to_book'))
            out['debt_to_equity'] = parse_number(metrics.get('debt_to_equity'))
            normalized[peer] = out

        return normalized

    def _fetch_market_data(self, ticker: str) -> Dict[str, Any]:
        """Fetch current market data from multiple sources"""
        market_data = {}

        # Try Finnhub first for real-time quote
        if self.finnhub:
            try:
                quote = self.finnhub.fetch_quote(ticker)
                market_data["realtime_quote"] = {
                    "current_price": quote.get("c"),
                    "open": quote.get("o"),
                    "high": quote.get("h"),
                    "low": quote.get("l"),
                    "close": quote.get("pc"),
                    "timestamp": quote.get("t"),
                    "bid": quote.get("b"),
                    "ask": quote.get("a"),
                    "bid_volume": quote.get("bv"),
                    "ask_volume": quote.get("av"),
                }
            except Exception as e:
                logger.warning(f"Finnhub quote fetch failed: {e}")

        # Try Alpha Vantage for time series data
        if self.alpha_vantage:
            try:
                overview = self.alpha_vantage.fetch_company_overview(ticker)
                market_data["company_overview"] = {
                    "market_cap": overview.get("MarketCapitalization"),
                    "pe_ratio": overview.get("PERatio"),
                    "dividend_yield": overview.get("DividendYield"),
                    "eps": overview.get("EPS"),
                    "revenue": overview.get("RevenueTTM"),
                    "profit_margin": overview.get("ProfitMargin"),
                    "beta": overview.get("Beta"),
                    "fifty_two_week_high": overview.get("52WeekHigh"),
                    "fifty_two_week_low": overview.get("52WeekLow"),
                }
            except Exception as e:
                logger.warning(f"Alpha Vantage overview fetch failed: {e}")

        # Try Yahoo Finance for additional market context
        if self.yahoo:
            try:
                yf_ticker = self.yahoo.Ticker(ticker)
                info = yf_ticker.info
                market_data["yahoo_info"] = {
                    "market_cap": info.get("marketCap"),
                    "trailing_pe": info.get("trailingPE"),
                    "forward_pe": info.get("forwardPE"),
                    "price_to_book": info.get("priceToBook"),
                    "debt_to_equity": info.get("debtToEquity"),
                    "current_ratio": info.get("currentRatio"),
                    "roe": info.get("returnOnEquity"),
                    "roa": info.get("returnOnAssets"),
                }
            except Exception as e:
                logger.warning(f"Yahoo Finance fetch failed: {e}")

        return market_data

    def _fetch_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Fetch detailed financial statements and fundamentals"""
        fundamentals = {}

        # Try Finnhub first
        if self.finnhub:
            try:
                # Income statement
                ic = self.finnhub.fetch_financials(ticker, "ic", "annual")
                if ic and "financials" in ic:
                    latest = ic["financials"][0] if ic["financials"] else {}
                    fundamentals["income_statement"] = {
                        "revenue": latest.get("revenue"),
                        "gross_profit": latest.get("grossProfit"),
                        "operating_income": latest.get("operatingIncome"),
                        "net_income": latest.get("netIncome"),
                        "period": latest.get("period"),
                    }
            except Exception as e:
                logger.debug(f"Finnhub income statement fetch failed: {e}")

            try:
                # Balance sheet
                bs = self.finnhub.fetch_financials(ticker, "bs", "annual")
                if bs and "financials" in bs:
                    latest = bs["financials"][0] if bs["financials"] else {}
                    fundamentals["balance_sheet"] = {
                        "total_assets": latest.get("totalAssets"),
                        "total_liabilities": latest.get("totalLiabilities"),
                        "total_equity": latest.get("totalEquity"),
                        "cash": latest.get("cashAndCashEquivalents"),
                        "period": latest.get("period"),
                    }
            except Exception as e:
                logger.debug(f"Finnhub balance sheet fetch failed: {e}")

            try:
                # Earnings calendar for trend
                earnings = self.finnhub.fetch_earnings_calendar(ticker, limit=10)
                fundamentals["earnings_history"] = earnings
            except Exception as e:
                logger.debug(f"Finnhub earnings calendar fetch failed: {e}")

        # Fallback to yfinance if Finnhub didn't provide income statement
        if not fundamentals.get("income_statement") and self.yahoo:
            try:
                yf = self.yahoo.Ticker(ticker)
                info = yf.info if hasattr(yf, 'info') else {}
                fundamentals["income_statement"] = {
                    "revenue": info.get("totalRevenue"),
                    "gross_profit": info.get("grossProfit"),
                    "operating_income": info.get("operatingCashflow"),
                    "net_income": info.get("netIncome"),
                    "period": "TTM"
                }
            except Exception as e:
                logger.debug(f"Yahoo Finance income statement fallback failed: {e}")

        # Fallback to Alpha Vantage overview for basic metrics
        if not fundamentals.get("income_statement") and self.alpha_vantage:
            try:
                overview = self.alpha_vantage.fetch_company_overview(ticker)
                if overview:
                    fundamentals["income_statement"] = {
                        "revenue": overview.get("RevenueTTM"),
                        "gross_profit": None,
                        "operating_income": None,
                        "net_income": overview.get("ProfitMargin"),
                        "period": "TTM"
                    }
            except Exception as e:
                logger.debug(f"Alpha Vantage overview fallback failed: {e}")

        return fundamentals

    def _fetch_company_profile(self, ticker: str) -> Dict[str, Any]:
        """Fetch company profile and background info"""
        profile = {}

        if self.finnhub:
            try:
                company_profile = self.finnhub.fetch_company_profile(ticker)
                profile = {
                    "name": company_profile.get("name"),
                    "country": company_profile.get("country"),
                    "currency": company_profile.get("currency"),
                    "exchange": company_profile.get("exchange"),
                    "industry": company_profile.get("finnhubIndustry"),
                    "ipo_date": company_profile.get("ipoDate"),
                    "market_cap": company_profile.get("marketCapitalization"),
                    "shares_outstanding": company_profile.get("shareOutstanding"),
                    "website": company_profile.get("weburl"),
                    "description": company_profile.get("description"),
                }
            except Exception as e:
                logger.warning(f"Company profile fetch failed: {e}")

        return profile

    def _fetch_news_sentiment(self, ticker: str, lookback_days: int) -> Dict[str, Any]:
        """Fetch recent news and sentiment indicators"""
        news_data = {"items": [], "sentiment_summary": {}, "article_download_summary": {}}

        if self.finnhub:
            try:
                end_date = datetime.now().date().isoformat()
                start_date = (datetime.now() - timedelta(days=lookback_days)).date().isoformat()
                
                news = self.finnhub.fetch_company_news(ticker, start_date, end_date)
                news_data["items"] = news[:20]  # Keep last 20 news items
                
                # Download full articles for verification
                try:
                    download_summary = self.article_downloader.download_articles(ticker, news[:20])
                    news_data["article_download_summary"] = download_summary
                    logger.info(f"Downloaded {download_summary['successful']} articles for {ticker}")
                except Exception as e:
                    logger.warning(f"Article download failed for {ticker}: {e}")
                    news_data["article_download_summary"] = {"error": str(e)}
                
                # Basic sentiment analysis
                positive = sum(1 for n in news if n.get("sentiment", 0) > 0.5)
                negative = sum(1 for n in news if n.get("sentiment", 0) < -0.5)
                neutral = len(news) - positive - negative
                
                news_data["sentiment_summary"] = {
                    "positive_count": positive,
                    "negative_count": negative,
                    "neutral_count": neutral,
                    "total_articles": len(news),
                    "sentiment_trend": "positive" if positive > negative else "negative" if negative > positive else "neutral"
                }
            except Exception as e:
                logger.warning(f"News sentiment fetch failed: {e}")

        return news_data

    def _fetch_earnings_analysis(self, ticker: str) -> Dict[str, Any]:
        """Fetch earnings history and estimates"""
        earnings = {}

        if self.finnhub:
            try:
                earnings_calendar = self.finnhub.fetch_earnings_calendar(ticker, limit=20)
                
                earnings["calendar"] = earnings_calendar
                
                # Calculate earnings trends
                if earnings_calendar:
                    eps_actual = [float(e.get("epsActual", 0) or 0) for e in earnings_calendar if e.get("epsActual")]
                    eps_estimate = [float(e.get("epsEstimate", 0) or 0) for e in earnings_calendar if e.get("epsEstimate")]
                    
                    if eps_actual and eps_estimate:
                        avg_actual = sum(eps_actual) / len(eps_actual)
                        avg_estimate = sum(eps_estimate) / len(eps_estimate)
                        earnings["eps_trend"] = {
                            "avg_actual": avg_actual,
                            "avg_estimate": avg_estimate,
                            "beat_rate": sum(1 for a, e in zip(eps_actual, eps_estimate) if a > e) / len(eps_estimate),
                            "last_surprise": (eps_actual[0] - eps_estimate[0]) / eps_estimate[0] if eps_estimate[0] else 0
                        }
            except Exception as e:
                logger.warning(f"Earnings analysis fetch failed: {e}")

        return earnings

    def _fetch_macroeconomic_context(self) -> Dict[str, Any]:
        """Fetch macroeconomic indicators from FRED"""
        macro = {}

        # Manual FRED API calls since we have the key
        try:
            import requests
            fred_key = os.getenv("FRED_API_KEY")
            if fred_key:
                indicators = {
                    "unemployment_rate": "UNRATE",
                    "gdp_growth": "A191RL1Q225SBEA",
                    "inflation": "CPIAUCSL",
                    "interest_rate": "DFF",
                    "consumer_sentiment": "UMCSENT",
                }
                
                for indicator, series_id in indicators.items():
                    try:
                        url = "https://api.stlouisfed.org/fred/series/observations"
                        params = {
                            "series_id": series_id,
                            "api_key": fred_key,
                            "file_type": "json",
                            "limit": 1,
                            "sort_order": "desc"
                        }
                        resp = requests.get(url, params=params, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            obs = data.get("observations", [])
                            if obs:
                                macro[indicator] = {
                                    "value": float(obs[0].get("value", 0)),
                                    "date": obs[0].get("date")
                                }
                    except Exception as e:
                        logger.warning(f"FRED {indicator} fetch failed: {e}")
        except Exception as e:
            logger.warning(f"Macroeconomic context fetch failed: {e}")

        return macro

    def _fetch_peer_analysis(self, ticker: str) -> Dict[str, Any]:
        """Fetch peer companies for comparison"""
        peers = {}

        if self.finnhub:
            try:
                peer_list = self.finnhub.fetch_symbol_peers(ticker)
                peers["peer_tickers"] = list(peer_list)[:5]  # Top 5 peers
                
                # Fetch basic metrics for peers
                peers["peer_metrics"] = self._fetch_peer_metrics(peers["peer_tickers"])
            except Exception as e:
                logger.warning(f"Peer analysis fetch failed: {e}")

        return peers

    def _fetch_peer_metrics(self, peer_list: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch basic metrics for a list of peer tickers using available clients"""
        peer_metrics: Dict[str, Dict[str, Any]] = {}

        for peer in peer_list:
            metrics: Dict[str, Any] = {}
            # Try Alpha Vantage overview first
            if self.alpha_vantage:
                try:
                    overview = self.alpha_vantage.fetch_company_overview(peer)
                    metrics["market_cap"] = overview.get("MarketCapitalization")
                    metrics["pe_ratio"] = overview.get("PERatio")
                    metrics["eps"] = overview.get("EPS")
                    metrics["revenue"] = overview.get("RevenueTTM")
                except Exception as e:
                    logger.debug(f"AlphaVantage peer overview failed for {peer}: {e}")

            # Fallback to Finnhub profile if needed
            if self.finnhub:
                try:
                    profile = self.finnhub.fetch_company_profile(peer)
                    # Finhub uses different field names; use what exists
                    if not metrics.get("market_cap") and profile.get("marketCapitalization"):
                        metrics["market_cap"] = profile.get("marketCapitalization")
                    if not metrics.get("pe_ratio") and profile.get("peRatio"):
                        metrics["pe_ratio"] = profile.get("peRatio")
                except Exception as e:
                    logger.debug(f"Finnhub peer profile failed for {peer}: {e}")

            # Include yahoo_info if available
            if self.yahoo:
                try:
                    yf_ticker = self.yahoo.Ticker(peer)
                    info = yf_ticker.info
                    if info:
                        if not metrics.get("pe_ratio"):
                            metrics["pe_ratio"] = info.get("trailingPE") or info.get("forwardPE")
                        if not metrics.get("market_cap"):
                            metrics["market_cap"] = info.get("marketCap")
                        metrics["price_to_book"] = info.get("priceToBook")
                        metrics["debt_to_equity"] = info.get("debtToEquity")
                except Exception as e:
                    logger.debug(f"Yahoo peer info failed for {peer}: {e}")

            peer_metrics[peer] = metrics

        return peer_metrics

    def _fetch_technical_analysis(self, ticker: str, lookback_days: int) -> Dict[str, Any]:
        """Fetch historical price data for technical analysis"""
        technicals = {}

        if self.alpha_vantage:
            try:
                df = self.alpha_vantage.fetch_time_series_daily(ticker, output_size="compact", adjusted=True)
                
                # Calculate technical indicators
                if len(df) > 0:
                    # Moving averages
                    sma_20 = df["close"].rolling(window=20).mean().iloc[-1]
                    sma_50 = df["close"].rolling(window=50).mean().iloc[-1]
                    
                    # Volatility
                    volatility = df["close"].pct_change().std()
                    
                    # Price momentum
                    price_momentum = (df["close"].iloc[-1] - df["close"].iloc[-20]) / df["close"].iloc[-20] if len(df) > 20 else 0
                    
                    technicals = {
                        "current_price": float(df["close"].iloc[-1]),
                        "52_week_high": float(df["high"].max()),
                        "52_week_low": float(df["low"].min()),
                        "sma_20": float(sma_20),
                        "sma_50": float(sma_50),
                        "volatility": float(volatility),
                        "20_day_momentum": float(price_momentum),
                        "data_points": len(df),
                    }
            except Exception as e:
                logger.warning(f"Technical analysis fetch failed: {e}")

        return technicals


def aggregate_company_data(ticker: str, lookback_days: int = 90) -> Dict[str, Any]:
    """Convenience function to aggregate all data for a ticker"""
    aggregator = ComprehensiveDataAggregator()
    return aggregator.aggregate_comprehensive_data(ticker, lookback_days)
