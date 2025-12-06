"""
Trading Signal Generator - Combine sentiment, metrics, and market data into trading signals
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum
import json


class SignalStrength(Enum):
    """Trading signal strength levels"""
    STRONG_BUY = 5
    BUY = 4
    HOLD = 3
    SELL = 2
    STRONG_SELL = 1


class SignalConfidence(Enum):
    """Confidence levels for signals"""
    VERY_HIGH = 0.9
    HIGH = 0.75
    MEDIUM = 0.6
    LOW = 0.45
    VERY_LOW = 0.3


@dataclass
class TradingSignal:
    """Container for trading signal output"""
    ticker: str
    signal_strength: SignalStrength
    confidence: float
    price_target_low: Optional[float]
    price_target_high: Optional[float]
    expected_move_percent_low: float
    expected_move_percent_high: float
    reasoning: Dict[str, str]  # Why we generated this signal
    factors: Dict[str, float]  # Individual factor scores (-1 to 1)
    recommendation: str  # Human-readable recommendation
    risks: List[str]
    catalysts: List[str]
    
    def to_dict(self):
        return {
            'ticker': self.ticker,
            'signal_strength': self.signal_strength.name,
            'confidence': self.confidence,
            'price_target': {
                'low': self.price_target_low,
                'high': self.price_target_high
            },
            'expected_move': {
                'low_percent': self.expected_move_percent_low,
                'high_percent': self.expected_move_percent_high
            },
            'reasoning': self.reasoning,
            'factors': self.factors,
            'recommendation': self.recommendation,
            'risks': self.risks,
            'catalysts': self.catalysts
        }


class SignalGenerator:
    """Generate trading signals from integrated analysis"""
    
    # Weights for different factors (sum should be 1.0)
    FACTOR_WEIGHTS = {
        'sentiment': 0.25,
        'eps_beat': 0.20,
        'revenue_growth': 0.15,
        'stock_momentum': 0.15,
        'market_sentiment': 0.15,
        'technical': 0.10
    }
    
    def __init__(self, current_price: float):
        self.current_price = current_price
    
    def generate_signal(
        self,
        ticker: str,
        sentiment_score: float,  # -1 to 1
        eps_beat: Optional[bool],
        revenue_growth: Optional[float],  # percentage
        stock_momentum: float,  # -1 to 1
        market_sentiment: float,  # -1 to 1
        metrics_data: Optional[Dict] = None,
        recent_news: Optional[List[str]] = None,
    ) -> TradingSignal:
        """
        Generate trading signal from multiple data sources
        
        Args:
            ticker: Stock ticker
            sentiment_score: NLP sentiment (-1 to 1)
            eps_beat: Whether company beat EPS expectations
            revenue_growth: Revenue growth percentage
            stock_momentum: Stock price momentum (-1 to 1)
            market_sentiment: Overall market sentiment (-1 to 1)
            metrics_data: Additional financial metrics
            recent_news: Recent news items for context
        """
        
        # Calculate individual factor scores
        factors = {
            'sentiment': sentiment_score,
            'eps_beat': 1.0 if eps_beat else (-0.5 if eps_beat is False else 0),
            'revenue_growth': self._normalize_revenue_growth(revenue_growth),
            'stock_momentum': stock_momentum,
            'market_sentiment': market_sentiment,
            'technical': self._calculate_technical_score(metrics_data)
        }
        
        # Calculate composite score
        composite_score = sum(
            factors.get(factor, 0) * self.FACTOR_WEIGHTS.get(factor, 0)
            for factor in self.FACTOR_WEIGHTS.keys()
        )
        
        # Determine signal strength and confidence
        signal_strength, confidence = self._interpret_score(composite_score, factors)
        
        # Calculate price targets
        price_target_low, price_target_high = self._calculate_price_targets(
            composite_score, confidence
        )
        expected_move_low = ((price_target_low - self.current_price) / self.current_price * 100) if price_target_low else 0
        expected_move_high = ((price_target_high - self.current_price) / self.current_price * 100) if price_target_high else 0
        
        # Generate reasoning
        reasoning = self._generate_reasoning(factors, eps_beat, revenue_growth)
        
        # Extract risks and catalysts
        risks = self._identify_risks(factors, metrics_data)
        catalysts = self._identify_catalysts(factors, recent_news)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(signal_strength, confidence)
        
        return TradingSignal(
            ticker=ticker,
            signal_strength=signal_strength,
            confidence=confidence,
            price_target_low=price_target_low,
            price_target_high=price_target_high,
            expected_move_percent_low=expected_move_low,
            expected_move_percent_high=expected_move_high,
            reasoning=reasoning,
            factors=factors,
            recommendation=recommendation,
            risks=risks,
            catalysts=catalysts
        )
    
    def _normalize_revenue_growth(self, growth_percent: Optional[float]) -> float:
        """Normalize revenue growth to -1 to 1 scale"""
        if growth_percent is None:
            return 0
        
        # Use sigmoid-like function
        if growth_percent > 30:
            return 1.0
        elif growth_percent > 15:
            return 0.7
        elif growth_percent > 5:
            return 0.3
        elif growth_percent > -5:
            return 0
        elif growth_percent > -15:
            return -0.3
        else:
            return -1.0
    
    def _calculate_technical_score(self, metrics_data: Optional[Dict]) -> float:
        """Calculate technical/fundamental score"""
        if not metrics_data:
            return 0
        
        score = 0
        
        # Gross margin analysis - handle nested dict structure
        if 'gross_margin' in metrics_data:
            margin_data = metrics_data['gross_margin']
            margin = margin_data.get('value') if isinstance(margin_data, dict) else margin_data
            if margin and margin > 50:
                score += 0.3
            elif margin and margin > 40:
                score += 0.15
        
        # EPS analysis - handle nested dict structure
        if 'eps' in metrics_data:
            eps_data = metrics_data['eps']
            eps_value = eps_data.get('value') if isinstance(eps_data, dict) else eps_data
            if eps_value and eps_value > 0:
                score += 0.3
        
        return min(1.0, score)
    
    def _interpret_score(self, composite_score: float, factors: Dict) -> tuple:
        """Convert composite score to signal strength and confidence"""
        # Confidence is based on consistency of signals
        factor_values = list(factors.values())
        avg_factor = sum(factor_values) / len(factor_values)
        consistency = 1 - (sum(abs(f - avg_factor) for f in factor_values) / len(factor_values) / 2)
        
        base_confidence = 0.5 + (abs(composite_score) * 0.4)
        confidence = base_confidence * (0.5 + consistency * 0.5)
        confidence = min(1.0, max(0.3, confidence))
        
        # Determine signal strength
        if composite_score > 0.6:
            signal = SignalStrength.STRONG_BUY
        elif composite_score > 0.2:
            signal = SignalStrength.BUY
        elif composite_score > -0.2:
            signal = SignalStrength.HOLD
        elif composite_score > -0.6:
            signal = SignalStrength.SELL
        else:
            signal = SignalStrength.STRONG_SELL
        
        return signal, confidence
    
    def _calculate_price_targets(self, composite_score: float, confidence: float) -> tuple:
        """Calculate price target range"""
        if not confidence or confidence < 0.3:
            return None, None
        
        # Use composite score to determine move magnitude
        move_magnitude = abs(composite_score) * confidence * 0.15  # Max 15% move
        
        if composite_score > 0:
            target_low = self.current_price * (1 + move_magnitude * 0.5)
            target_high = self.current_price * (1 + move_magnitude * 1.5)
        else:
            target_low = self.current_price * (1 - move_magnitude * 1.5)
            target_high = self.current_price * (1 - move_magnitude * 0.5)
        
        return round(target_low, 2), round(target_high, 2)
    
    def _generate_reasoning(self, factors: Dict, eps_beat: Optional[bool], revenue_growth: Optional[float]) -> Dict[str, str]:
        """Generate human-readable reasoning for the signal"""
        reasoning = {}
        
        if factors['sentiment'] > 0.5:
            reasoning['sentiment'] = f"Positive sentiment from earnings report ({factors['sentiment']:.2f})"
        elif factors['sentiment'] < -0.5:
            reasoning['sentiment'] = f"Negative sentiment from earnings report ({factors['sentiment']:.2f})"
        else:
            reasoning['sentiment'] = "Neutral sentiment from earnings report"
        
        if eps_beat:
            reasoning['earnings'] = "Company beat EPS expectations"
        elif eps_beat is False:
            reasoning['earnings'] = "Company missed EPS expectations"
        
        if revenue_growth and revenue_growth > 15:
            reasoning['revenue'] = f"Strong revenue growth of {revenue_growth:.1f}%"
        elif revenue_growth and revenue_growth < -5:
            reasoning['revenue'] = f"Revenue declined {abs(revenue_growth):.1f}%"
        
        if factors['stock_momentum'] > 0.5:
            reasoning['momentum'] = "Stock showing positive momentum"
        elif factors['stock_momentum'] < -0.5:
            reasoning['momentum'] = "Stock showing negative momentum"
        
        return reasoning
    
    def _identify_risks(self, factors: Dict, metrics_data: Optional[Dict]) -> List[str]:
        """Identify key risks"""
        risks = []
        
        if factors['sentiment'] < 0:
            risks.append("Negative sentiment in earnings report")
        
        if factors['market_sentiment'] < -0.3:
            risks.append("Broader market sentiment is negative")
        
        if factors['stock_momentum'] < -0.3:
            risks.append("Stock momentum is declining")
        
        if metrics_data and 'gross_margin' in metrics_data and metrics_data['gross_margin'] < 30:
            risks.append("Low gross margins suggest profitability concerns")
        
        if not risks:
            risks.append("Standard market volatility")
        
        return risks
    
    def _identify_catalysts(self, factors: Dict, recent_news: Optional[List[str]]) -> List[str]:
        """Identify potential catalysts"""
        catalysts = []
        
        if factors['sentiment'] > 0.5:
            catalysts.append("Positive earnings sentiment could drive upside")
        
        if factors['revenue_growth'] > 0.5:
            catalysts.append("Strong revenue growth momentum")
        
        if recent_news:
            catalysts.append(f"Recent developments: {recent_news[0][:60]}...")
        
        if not catalysts:
            catalysts.append("Next earnings release")
        
        return catalysts
    
    def _generate_recommendation(self, signal_strength: SignalStrength, confidence: float) -> str:
        """Generate human-readable recommendation"""
        if signal_strength == SignalStrength.STRONG_BUY:
            return f"STRONG BUY - High conviction opportunity (confidence: {confidence:.0%})"
        elif signal_strength == SignalStrength.BUY:
            return f"BUY - Positive outlook (confidence: {confidence:.0%})"
        elif signal_strength == SignalStrength.HOLD:
            return f"HOLD - Neutral bias (confidence: {confidence:.0%})"
        elif signal_strength == SignalStrength.SELL:
            return f"SELL - Cautious outlook (confidence: {confidence:.0%})"
        else:
            return f"STRONG SELL - Negative conviction (confidence: {confidence:.0%})"
