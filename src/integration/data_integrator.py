"""
Data Integration Layer - Combine all data sources into unified format
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import json
from datetime import datetime


@dataclass
class IntegratedAnalysis:
    """Complete analysis combining all data sources"""
    ticker: str
    company_name: Optional[str]
    analysis_date: str
    
    # Sentiment Analysis
    sentiment: Dict
    
    # Financial Metrics
    financial_metrics: Dict
    
    # Market Data
    stock_data: Dict
    economic_data: Dict
    fundamentals: Dict
    
    # News
    recent_news: List[str]
    
    # Trading Signal
    trading_signal: Dict
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(asdict(self), indent=2, default=str)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def save_to_file(self, filepath: str):
        """Save analysis to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        lines = [
            "=" * 80,
            "INTEGRATED FINANCIAL ANALYSIS REPORT",
            "=" * 80,
            f"Ticker: {self.ticker}",
            f"Company: {self.company_name}",
            f"Analysis Date: {self.analysis_date}",
            "",
            "SENTIMENT ANALYSIS",
            "-" * 80,
        ]
        
        for section, results in self.sentiment.get('sections', {}).items():
            lines.append(f"  {section:30s} → {results.get('sentiment', 'N/A').upper():10s}")
        
        lines.extend([
            "",
            "FINANCIAL METRICS (from earnings report)",
            "-" * 80,
        ])
        
        for metric, data in self.financial_metrics.items():
            if isinstance(data, dict):
                value = data.get('value', 'N/A')
                unit = data.get('unit', '')
                lines.append(f"  {metric:30s} → {value} {unit}")
        
        lines.extend([
            "",
            "STOCK DATA",
            "-" * 80,
        ])
        
        if self.stock_data:
            current_price = self.stock_data.get('current_price')
            pe_ratio = self.stock_data.get('pe_ratio')
            price_change = self.stock_data.get('price_change_percent')
            lines.append(f"  Current Price: ${current_price}")
            lines.append(f"  P/E Ratio: {pe_ratio}")
            lines.append(f"  Year-to-Date Change: {price_change}%")
        
        lines.extend([
            "",
            "TRADING SIGNAL",
            "-" * 80,
            f"  Recommendation: {self.trading_signal.get('recommendation', 'N/A')}",
            f"  Signal Strength: {self.trading_signal.get('signal_strength', 'N/A')}",
            f"  Confidence: {self.trading_signal.get('confidence', 0):.0%}",
        ])
        
        if self.trading_signal.get('price_target'):
            pt = self.trading_signal['price_target']
            lines.append(f"  Price Target: ${pt.get('low')} - ${pt.get('high')}")
        
        lines.extend([
            "",
            "RISKS",
            "-" * 80,
        ])
        for risk in self.trading_signal.get('risks', []):
            lines.append(f"  • {risk}")
        
        lines.extend([
            "",
            "CATALYSTS",
            "-" * 80,
        ])
        for catalyst in self.trading_signal.get('catalysts', []):
            lines.append(f"  • {catalyst}")
        
        lines.append("=" * 80)
        
        return "\n".join(lines)


class DataIntegrator:
    """Combine all data sources into unified analysis"""
    
    @staticmethod
    def integrate(
        ticker: str,
        company_name: Optional[str],
        sentiment_results: Dict,
        financial_metrics: Dict,
        stock_data: Dict,
        economic_data: Dict,
        fundamentals: Dict,
        recent_news: List[str],
        trading_signal: Dict,
    ) -> IntegratedAnalysis:
        """
        Combine all analysis components into single integrated report
        
        Args:
            ticker: Stock ticker
            company_name: Company name
            sentiment_results: Sentiment analysis from FinBERT
            financial_metrics: Extracted financial metrics
            stock_data: Stock price and technical data
            economic_data: Economic indicators (FRED)
            fundamentals: Company fundamentals
            recent_news: Recent news items
            trading_signal: Generated trading signal
        
        Returns:
            IntegratedAnalysis object with all data combined
        """
        return IntegratedAnalysis(
            ticker=ticker,
            company_name=company_name,
            analysis_date=datetime.now().isoformat(),
            sentiment=sentiment_results,
            financial_metrics=financial_metrics,
            stock_data=stock_data,
            economic_data=economic_data,
            fundamentals=fundamentals,
            recent_news=recent_news,
            trading_signal=trading_signal
        )
