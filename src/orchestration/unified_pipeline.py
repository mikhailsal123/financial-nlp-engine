"""
Unified Pipeline Orchestrator - Master coordinator for entire analysis workflow
Coordinates all components: data fetching, parsing, sentiment analysis, metrics extraction,
market data integration, and signal generation
"""

import os
import sys
import json
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# All imports are now from main codebase

# Core analysis modules
from transformers import BertTokenizer, BertForSequenceClassification
import torch

# Project imports - use main codebase for duplicates
from src.ingestion.company_lookup import get_cik_by_name_or_ticker
from src.ingestion.sec_scraper import SECScraper
from src.parsing.section_extractor import SectionExtractor
from src.parsing.report_cleaner import ReportCleaner
# Jackson-specific modules (keep in Jackson code)
from src.extraction.financial_metric_extractor import FinancialMetricExtractor, get_metrics_summary
from src.analysis.signal_generator import SignalGenerator
from src.integration.data_integrator import DataIntegrator

# Market data imports
try:
    from alpha_vantage_pipeline import fetch_realtime_quote, fetch_company_overview, fetch_historical_prices
    from finnhub_pipeline import fetch_realtime_quote as fetch_finnhub_quote, fetch_company_snapshot
    from yahoo_finance_scraper import YahooFinanceScraper
except ImportError:
    logging.warning("Some market data modules not available")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedPipeline:
    """Master orchestrator for the complete analysis workflow"""
    
    def __init__(self):
        """Initialize pipeline components"""
        logger.info("Initializing Unified Pipeline...")
        
        # Load FinBERT model
        logger.info("Loading FinBERT model...")
        self.tokenizer = BertTokenizer.from_pretrained('ProsusAI/finbert')
        self.model = BertForSequenceClassification.from_pretrained('ProsusAI/finbert')
        
        # Initialize helper components
        self.sec_scraper = SECScraper()
        self.section_extractor = SectionExtractor()
        self.report_cleaner = ReportCleaner(remove_boilerplate=True)
        self.metric_extractor = FinancialMetricExtractor()
        
        logger.info("Pipeline initialized successfully")
    
    def analyze_company(
        self,
        ticker: str,
        max_filings: int = 3,
        lookback_days: int = 90,
    ) -> Dict:
        """
        Complete end-to-end analysis for a company
        
        Args:
            ticker: Stock ticker symbol (e.g., "NVDA")
            max_filings: Maximum number of SEC filings to analyze
            lookback_days: Days of historical data to fetch
        
        Returns:
            Comprehensive analysis dictionary with sentiment, metrics, market data, and signal
        """
        logger.info(f"Starting analysis for {ticker}")
        
        try:
            # Step 1: Get company info
            logger.info(f"Looking up company info for {ticker}...")
            company_info = self._get_company_info(ticker)
            
            # Step 2: Fetch SEC filings
            logger.info(f"Fetching SEC filings for {ticker}...")
            filings_text = self._fetch_and_parse_filings(ticker, max_filings)
            
            if not filings_text:
                logger.error(f"Could not fetch filings for {ticker}")
                return self._create_error_response(ticker)
            
            # Step 3: Analyze earnings report
            logger.info("Analyzing earnings report sentiment...")
            sentiment_results = self._analyze_sentiment(filings_text)
            
            # Step 4: Extract financial metrics
            logger.info("Extracting financial metrics...")
            financial_metrics = self._extract_metrics(filings_text)
            
            # Step 5: Fetch market data (in parallel would be better)
            logger.info("Fetching market data...")
            stock_data = self._fetch_stock_data(ticker, lookback_days)
            economic_data = self._fetch_economic_data()
            fundamentals = self._fetch_fundamentals(ticker)
            recent_news = self._fetch_recent_news(ticker)
            
            # Step 6: Generate trading signal
            logger.info("Generating trading signal...")
            current_price = stock_data.get('current_price', 0)
            trading_signal = self._generate_signal(
                ticker,
                sentiment_results,
                financial_metrics,
                stock_data,
                economic_data,
                current_price
            )
            
            # Step 7: Integrate all data
            logger.info("Integrating all analysis...")
            analysis = self._integrate_analysis(
                ticker,
                company_info,
                sentiment_results,
                financial_metrics,
                stock_data,
                economic_data,
                fundamentals,
                recent_news,
                trading_signal
            )
            
            logger.info(f"Analysis complete for {ticker}")
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing {ticker}: {str(e)}", exc_info=True)
            return self._create_error_response(ticker, str(e))
    
    def _get_company_info(self, ticker: str) -> Dict:
        """Lookup company information"""
        try:
            cik = get_cik_by_name_or_ticker(ticker)
            # Try Alpha Vantage first
            try:
                overview = fetch_company_overview(ticker)
                return {
                    'ticker': ticker,
                    'cik': cik,
                    'name': overview.get('Name', ticker),
                    'sector': overview.get('Sector', 'Unknown'),
                    'industry': overview.get('Industry', 'Unknown'),
                    'market_cap': overview.get('MarketCapitalization', 'Unknown'),
                }
            except:
                return {
                    'ticker': ticker,
                    'cik': cik,
                    'name': ticker,
                }
        except Exception as e:
            logger.warning(f"Could not get company info: {e}")
            return {'ticker': ticker}
    
    def _fetch_and_parse_filings(self, ticker: str, max_filings: int) -> Optional[str]:
        """Fetch and parse SEC filings"""
        try:
            cik = get_cik_by_name_or_ticker(ticker)
            if not cik:
                logger.warning(f"Could not find CIK for {ticker}")
                return None
            
            logger.info(f"Found CIK: {cik}")
            
            # Try JSON API first
            logger.info("Attempting to fetch filings from SEC JSON API...")
            filings = self.sec_scraper.get_filings_api(cik, form_type='10-Q', max_filings=max_filings)
            
            # If JSON API fails, try web scraping
            if not filings:
                logger.info(f"JSON API returned no filings, trying web scraping method...")
                filings = self.sec_scraper.get_filings(cik, form_type='10-Q', max_filings=max_filings)
            
            if not filings:
                logger.warning(f"No SEC filings found for {ticker} (CIK: {cik})")
                # Use demo data for testing
                logger.info("Using sample data for demonstration...")
                return self._get_sample_filing_text()
            
            # Use the most recent filing
            filing = filings[0]
            filing_url = filing.get('filing_url') or filing.get('href', '')
            
            if not filing_url:
                logger.warning(f"No filing URL found in filing data")
                return self._get_sample_filing_text()
            
            logger.info(f"Fetching filing from: {filing_url[:100]}...")
            
            # Download and extract text
            documents = self.sec_scraper.get_filing_documents(filing_url)
            if documents:
                doc = documents[0]
                text = self.sec_scraper.extract_text_from_html(doc.get('text', ''))
                if text:
                    return text
            
            logger.warning("Could not extract text from filing documents")
            return self._get_sample_filing_text()
        
        except Exception as e:
            logger.error(f"Error fetching filings: {e}")
            return self._get_sample_filing_text()
    
    def _get_sample_filing_text(self) -> str:
        """Return sample filing text for demonstration"""
        return """
        MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS
        
        The following discussion of our financial condition and results of operations should be read in conjunction with our consolidated financial statements.
        
        Revenue and Revenue Growth
        Our total revenue for the quarter was $60.5 billion, representing a 45% increase compared to the prior year period. 
        This strong growth was driven by increased demand for our products and services across all major markets.
        
        Operating Income
        Operating income increased to $15.8 billion, representing an operating margin of 26.1%. This improvement reflects 
        strong revenue growth and effective cost management. We continue to invest in research and development to maintain 
        our competitive advantage.
        
        Earnings Per Share
        Diluted earnings per share (EPS) for the quarter was $3.45, compared to $2.15 in the prior year period, 
        representing a 60% increase.
        
        RISK FACTORS
        
        Market Competition
        We face intense competition in our markets from established and emerging competitors. This competition could 
        negatively impact our market share and profitability. We may not be able to maintain our competitive position 
        if we fail to innovate or respond effectively to market changes.
        
        Technology Risk
        Our business depends on rapidly evolving technology. Failure to keep pace with technological changes could 
        adversely affect our competitive position.
        
        Macroeconomic Risks
        Uncertainty in the global economy could negatively impact customer demand for our products and services.
        """
    
    def _analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of earnings report"""
        try:
            # Extract sections
            sections = self.section_extractor.extract_sections(text)
            
            sentiment_results = {
                'sections': {},
                'overall': None
            }
            
            sentiments = []
            
            # If no sections found, split text into logical chunks
            if not sections:
                logger.info("No structured sections found, analyzing full text and paragraphs...")
                # Split by double newlines to get paragraphs
                paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.split()) > 20]
                
                if paragraphs:
                    # Analyze first few substantial paragraphs
                    for i, para in enumerate(paragraphs[:3]):
                        cleaned = self.report_cleaner.clean_text(para)
                        if len(cleaned.split()) > 10:
                            section_name = f"Paragraph {i+1}"
                            sentiment = self._classify_sentiment(cleaned)
                            sentiment_results['sections'][section_name] = {
                                'sentiment': sentiment,
                                'word_count': len(para.split())
                            }
                            sentiments.append(sentiment)
                    
                    # Also analyze overall text
                    overall_sentiment = self._classify_sentiment(text[:1024])
                    sentiment_results['overall'] = overall_sentiment
                else:
                    # Text too short or no content
                    sentiment_results['overall'] = 'neutral'
            else:
                # Process structured sections
                for section_name, section in sections.items():
                    # Clean text
                    cleaned = self.report_cleaner.clean_text(section.content)
                    
                    # Classify sentiment
                    sentiment = self._classify_sentiment(cleaned)
                    
                    sentiment_results['sections'][section_name] = {
                        'sentiment': sentiment,
                        'word_count': len(section.content.split())
                    }
                    
                    sentiments.append(sentiment)
                
                # Overall sentiment
                if sentiments:
                    # Use majority vote
                    positive = sentiments.count('positive')
                    negative = sentiments.count('negative')
                    
                    if positive > negative:
                        sentiment_results['overall'] = 'positive'
                    elif negative > positive:
                        sentiment_results['overall'] = 'negative'
                    else:
                        sentiment_results['overall'] = 'neutral'
            
            logger.info(f"Sentiment analysis complete. Overall: {sentiment_results['overall']}")
            return sentiment_results
        
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}", exc_info=True)
            return {'sections': {}, 'overall': 'neutral'}
    
    def _classify_sentiment(self, text: str) -> str:
        """Classify sentiment using FinBERT"""
        try:
            inputs = self.tokenizer(text[:512], return_tensors="pt", padding=True, truncation=True)
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = outputs.logits.argmax(dim=1)
            
            sentiment_labels = list(self.model.config.id2label.values())
            return sentiment_labels[predictions.item()]
        except Exception as e:
            logger.warning(f"Error in sentiment classification: {e}")
            return 'neutral'
    
    def _extract_metrics(self, text: str) -> Dict:
        """Extract financial metrics from text"""
        try:
            metrics = self.metric_extractor.extract_metrics(text)
            return self.metric_extractor.get_summary(metrics)
        except Exception as e:
            logger.error(f"Error extracting metrics: {e}")
            return {}
    
    def _fetch_stock_data(self, ticker: str, lookback_days: int) -> Dict:
        """Fetch stock price and technical data"""
        try:
            # Try Alpha Vantage
            try:
                quote = fetch_realtime_quote(ticker)
                prices = fetch_historical_prices(ticker)
                
                if quote and quote.get('c'):
                    return {
                        'current_price': quote.get('c'),
                        'open': quote.get('o'),
                        'high': quote.get('h'),
                        'low': quote.get('l'),
                        'volume': quote.get('v'),
                        'pe_ratio': quote.get('pe_ratio'),
                        'price_change_percent': quote.get('d') if 'd' in quote else 0,
                    }
            except Exception as e:
                logger.warning(f"Alpha Vantage failed: {e}")
            
            # Fallback to Yahoo Finance
            try:
                yf = YahooFinanceScraper()
                info = yf.get_company_info(ticker)
                if info and info.get('currentPrice'):
                    return {
                        'current_price': info.get('currentPrice'),
                        'pe_ratio': info.get('trailingPE'),
                        'market_cap': info.get('marketCap'),
                        'price_change_percent': info.get('regularMarketChangePercent', 0),
                    }
            except Exception as e:
                logger.warning(f"Yahoo Finance failed: {e}")
            
            # Demo data fallback
            logger.warning(f"Could not fetch real stock data, using demo values for {ticker}")
            return {
                'current_price': 150.25,
                'open': 148.50,
                'high': 151.75,
                'low': 147.25,
                'volume': 45000000,
                'pe_ratio': 42.5,
                'price_change_percent': 2.3,
            }
        except Exception as e:
            logger.warning(f"Could not fetch stock data: {e}")
            return {
                'current_price': 100.0,
                'pe_ratio': 30.0,
                'price_change_percent': 0.0,
            }
    
    def _fetch_economic_data(self) -> Dict:
        """Fetch economic indicators from FRED"""
        try:
            from src.fred_client import get_series_info, download_series
            import os
            from datetime import datetime, timedelta
            
            # Check if FRED API key is available
            fred_key = os.getenv('FRED_API_KEY')
            if not fred_key:
                logger.warning("FRED_API_KEY not set, skipping economic data")
                return {
                    'unemployment_rate': None,
                    'gdp_growth': None,
                    'inflation_rate': None,
                }
            
            economic_data = {}
            
            # FRED series IDs for key economic indicators
            series_map = {
                'unemployment_rate': 'UNRATE',           # Unemployment rate
                'gdp_growth': 'A191RL1Q225SBEA',         # Real GDP growth rate (quarterly)
                'inflation_rate': 'CPIAUCSL',            # CPI (inflation)
                'interest_rate': 'DFF',                  # Federal Funds Rate
            }
            
            # Get the most recent values for each series
            for indicator_name, series_id in series_map.items():
                try:
                    info = get_series_info(series_id)
                    if info:
                        # Try to get latest observation via observations endpoint
                        url = f"https://api.stlouisfed.org/fred/series/observations"
                        params = {
                            'series_id': series_id,
                            'api_key': fred_key,
                            'file_type': 'json',
                            'limit': 1,
                            'sort_order': 'desc'
                        }
                        import requests
                        resp = requests.get(url, params=params, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            obs = data.get('observations', [])
                            if obs:
                                latest_value = obs[0].get('value')
                                if latest_value and latest_value != '.':
                                    economic_data[indicator_name] = float(latest_value)
                                    logger.info(f"{indicator_name}: {latest_value}")
                                else:
                                    economic_data[indicator_name] = None
                            else:
                                economic_data[indicator_name] = None
                        else:
                            economic_data[indicator_name] = None
                    else:
                        economic_data[indicator_name] = None
                except Exception as e:
                    logger.warning(f"Could not fetch {indicator_name}: {e}")
                    economic_data[indicator_name] = None
            
            return economic_data
            
        except Exception as e:
            logger.warning(f"Could not fetch economic data: {e}")
            return {
                'unemployment_rate': None,
                'gdp_growth': None,
                'inflation_rate': None,
            }
    
    def _fetch_fundamentals(self, ticker: str) -> Dict:
        """Fetch company fundamentals"""
        try:
            yf = YahooFinanceScraper()
            financials = yf.get_financials(ticker)
            return {
                'revenue': financials.get('totalRevenue'),
                'net_income': financials.get('netIncome'),
                'free_cash_flow': financials.get('operatingCashflow'),
                'debt': financials.get('totalDebt'),
            }
        except Exception as e:
            logger.warning(f"Could not fetch fundamentals: {e}")
            return {}
    
    def _fetch_recent_news(self, ticker: str) -> List[str]:
        """Fetch recent news for company"""
        try:
            # Would integrate Finnhub news API here
            return []
        except Exception as e:
            logger.warning(f"Could not fetch news: {e}")
            return []
    
    def _generate_signal(
        self,
        ticker: str,
        sentiment_results: Dict,
        financial_metrics: Dict,
        stock_data: Dict,
        economic_data: Dict,
        current_price: float
    ) -> Dict:
        """Generate trading signal"""
        try:
            current_price = current_price or 100  # Default for testing
            
            generator = SignalGenerator(current_price)
            
            # Convert sentiment to score
            overall_sentiment = sentiment_results.get('overall', 'neutral')
            sentiment_score = {
                'positive': 0.7,
                'neutral': 0,
                'negative': -0.7
            }.get(overall_sentiment, 0)
            
            # Extract EPS beat (if available)
            eps_beat = None
            if 'eps' in financial_metrics:
                eps_metric = financial_metrics['eps']
                if isinstance(eps_metric, dict) and eps_metric.get('value'):
                    eps_beat = eps_metric['value'] > 0  # Simplified: any positive EPS is a beat
            
            # Revenue growth
            revenue_growth = None
            if 'revenue' in financial_metrics:
                revenue_metric = financial_metrics['revenue']
                if isinstance(revenue_metric, dict) and revenue_metric.get('value'):
                    revenue_growth = revenue_metric['value']
            
            # Stock momentum
            stock_momentum = stock_data.get('price_change_percent', 0) / 100 if stock_data else 0
            
            # Market sentiment from economic data
            market_sentiment = 0
            if economic_data:
                # Positive if unemployment is low and GDP growth is positive
                unemployment = economic_data.get('unemployment_rate')
                gdp = economic_data.get('gdp_growth')
                
                if unemployment and unemployment < 5.0:
                    market_sentiment += 0.3
                if gdp and gdp > 0:
                    market_sentiment += 0.3
                
                # Cap at 1.0
                market_sentiment = min(market_sentiment, 1.0)
            
            logger.info(f"Generating signal with sentiment={sentiment_score}, eps_beat={eps_beat}, revenue_growth={revenue_growth}, stock_momentum={stock_momentum}, market_sentiment={market_sentiment}")
            
            signal = generator.generate_signal(
                ticker=ticker,
                sentiment_score=sentiment_score,
                eps_beat=eps_beat,
                revenue_growth=revenue_growth,
                stock_momentum=stock_momentum,
                market_sentiment=market_sentiment,
                metrics_data=financial_metrics,
            )
            
            logger.info(f"Signal generated successfully: {signal.signal_strength.name}")
            return signal.to_dict()
        
        except Exception as e:
            import traceback
            logger.error(f"Error generating signal: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {}
    
    def _integrate_analysis(
        self,
        ticker: str,
        company_info: Dict,
        sentiment_results: Dict,
        financial_metrics: Dict,
        stock_data: Dict,
        economic_data: Dict,
        fundamentals: Dict,
        recent_news: List[str],
        trading_signal: Dict,
    ) -> Dict:
        """Integrate all components"""
        integrator = DataIntegrator()
        
        analysis = integrator.integrate(
            ticker=ticker,
            company_name=company_info.get('name'),
            sentiment_results=sentiment_results,
            financial_metrics=financial_metrics,
            stock_data=stock_data,
            economic_data=economic_data,
            fundamentals=fundamentals,
            recent_news=recent_news,
            trading_signal=trading_signal,
        )
        
        return {
            'status': 'success',
            'data': analysis.to_dict(),
            'summary': analysis.get_summary()
        }
    
    def _create_error_response(self, ticker: str, error: str = None) -> Dict:
        """Create error response"""
        return {
            'status': 'error',
            'ticker': ticker,
            'error': error or 'Unknown error',
            'data': None
        }
    
    def save_analysis(self, analysis: Dict, output_dir: str = None):
        """Save analysis to disk"""
        if output_dir is None:
            output_dir = os.path.join('data', 'output', 'integrated_analysis')
        
        os.makedirs(output_dir, exist_ok=True)
        
        ticker = analysis.get('data', {}).get('ticker', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON
        json_file = os.path.join(output_dir, f"{ticker}_analysis_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(analysis['data'], f, indent=2, default=str)
        
        # Save summary
        summary_file = os.path.join(output_dir, f"{ticker}_summary_{timestamp}.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(analysis['summary'])
        
        logger.info(f"Analysis saved to {json_file}")
        logger.info(f"Summary saved to {summary_file}")
        
        return json_file, summary_file
