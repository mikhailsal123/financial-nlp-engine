"""
Financial Metric Extractor - Extract key metrics from earnings reports
Extracts: EPS, revenue, guidance, margins, growth rates, and other key financial metrics
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class FinancialMetric:
    """Container for extracted financial metrics"""
    metric_name: str
    value: float
    unit: str  # e.g., "dollars", "billions", "percent"
    context: str  # surrounding text context
    confidence: float  # 0.0-1.0 confidence score
    period: Optional[str] = None  # e.g., "Q3 2025", "FY 2025"


class FinancialMetricExtractor:
    """Extract quantitative financial metrics from earnings report text"""
    
    # Pattern definitions for different metrics
    PATTERNS = {
        'eps': [
            r'(?:earnings\s+per\s+share|EPS|diluted\s+earnings\s+per\s+share)[^$]*?\$?([\d.]+)',
            r'EPS[\s:]?(?:of|was)?[\s:]*\$?([\d.]+)',
            r'diluted\s+EPS[\s:]*\$?([\d.]+)',
            r'EPS\s+(?:of\s+)?\$?([\d.]+)',
        ],
        'revenue': [
            r'(?:total\s+)?revenue[^$]*?\$?([\d.]+)\s*(?:billion|million|B|M)',
            r'revenues[^$]*?\$?([\d.]+)\s*(?:billion|million|B|M)',
        ],
        'net_income': [
            r'net\s+income[^$]*?\$?([\d.]+)\s*(?:billion|million|B|M)',
            r'net\s+profit[^$]*?\$?([\d.]+)\s*(?:billion|million|B|M)',
        ],
        'operating_income': [
            r'operating\s+income[^$]*?\$?([\d.]+)\s*(?:billion|million|B|M)',
        ],
        'gross_margin': [
            r'gross\s+margin[\s:]*(\d+\.?\d*)\s*%',
            r'gross\s+margin(?:\s+was)?[\s:]*(\d+\.?\d*)\s*%',
        ],
        'operating_margin': [
            r'operating\s+margin[\s:]*(\d+\.?\d*)\s*%',
        ],
        'growth_rate': [
            r'(?:revenue|earnings|sales)[\s.]*(?:growth|increased?|grew|up)[\s:]*(\d+\.?\d*)\s*%',
            r'year(?:-|\s)?over(?:-|\s)?year[\s.]*(\d+\.?\d*)\s*%',
            r'increase[d]?[\s.]*(\d+\.?\d*)\s*%',
            r'(?:increased?|growth|grew)\s+(?:by\s+)?(\d+\.?\d*)\s*%',
        ],
        'guidance': [
            r'guidance[^$]*?(?:\$|[\d.])\s*([\d.]+)\s*(?:billion|million|B|M)',
            r'(?:expect|outlook|forecast)[^$]*?(?:\$|[\d.])\s*([\d.]+)\s*(?:billion|million|B|M)',
        ],
        'tax_rate': [
            r'(?:effective\s+)?tax\s+rate[\s:]*(\d+\.?\d*)\s*%',
        ],
    }
    
    def __init__(self):
        self.compiled_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for efficiency"""
        compiled = {}
        for metric, patterns in self.PATTERNS.items():
            compiled[metric] = [re.compile(p, re.IGNORECASE) for p in patterns]
        return compiled
    
    def extract_metrics(self, text: str) -> Dict[str, List[FinancialMetric]]:
        """
        Extract all financial metrics from text
        
        Args:
            text: Earnings report text
            
        Returns:
            Dictionary of metric_type -> list of FinancialMetric objects
        """
        results = {}
        
        for metric_type, patterns in self.compiled_patterns.items():
            metrics = []
            for pattern in patterns:
                matches = pattern.finditer(text)
                for match in matches:
                    metric = self._parse_match(metric_type, match, text)
                    if metric and metric.confidence > 0.5:
                        metrics.append(metric)
            
            if metrics:
                results[metric_type] = metrics
        
        return results
    
    def _parse_match(self, metric_type: str, match: re.Match, text: str) -> Optional[FinancialMetric]:
        """Parse a regex match into a FinancialMetric"""
        try:
            value_str = match.group(1)
            full_match = match.group(0)  # Get full matched text
            
            # Extract period if available
            period = self._extract_period(text, match.start())
            
            # Get context (surrounding text)
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end].strip()
            
            # Parse value and unit (pass full match to detect units)
            value, unit = self._parse_value(value_str, metric_type, full_match)
            
            if value is None:
                return None
            
            # Determine confidence based on context
            confidence = self._calculate_confidence(context, metric_type)
            
            return FinancialMetric(
                metric_name=metric_type,
                value=value,
                unit=unit,
                context=context,
                confidence=confidence,
                period=period
            )
        except Exception:
            return None
    
    def _parse_value(self, value_str: str, metric_type: str, full_match: str = "") -> Tuple[Optional[float], str]:
        """Parse value string and determine unit"""
        value_str = value_str.strip()
        full_match = full_match.lower()
        
        # Check for billion/million in full match or value string
        if 'billion' in full_match or 'b' in full_match:
            try:
                return float(value_str.split()[0]), 'billions'
            except:
                return float(value_str), 'billions'
        elif 'million' in full_match or 'm' in full_match:
            try:
                return float(value_str.split()[0]), 'millions'
            except:
                return float(value_str), 'millions'
        
        try:
            value = float(value_str)
            
            # Infer unit from metric type
            if metric_type in ['eps']:
                return value, 'dollars'
            elif metric_type in ['gross_margin', 'operating_margin', 'tax_rate', 'growth_rate']:
                return value, 'percent'
            else:
                return value, 'dollars'
        except ValueError:
            return None, ''
    
    def _extract_period(self, text: str, position: int) -> Optional[str]:
        """Extract reporting period near the metric"""
        # Look backwards for quarter/year references
        context = text[max(0, position - 200):position]
        
        period_patterns = [
            r'(?:Q|quarter)\s+(\d)\s+(?:of\s+)?(?:fiscal\s+)?(?:year\s+)?(\d{4})',
            r'(?:fiscal\s+)?(\d{4})\s+(?:Q|quarter)\s+(\d)',
            r'(?:for\s+the\s+)?(?:three|six|nine)\s+months?\s+(?:ended?|ended)?\s*(\w+\s+\d+,?\s+\d{4})',
        ]
        
        for pattern in period_patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _calculate_confidence(self, context: str, metric_type: str) -> float:
        """Calculate confidence score based on context quality"""
        confidence = 0.7  # Base confidence
        
        # Boost confidence for specific phrases
        if any(phrase in context.lower() for phrase in ['reported', 'announced', 'results', 'earned']):
            confidence += 0.15
        
        # Reduce confidence for forward-looking/uncertain language
        if any(phrase in context.lower() for phrase in ['expect', 'estimate', 'could', 'may', 'might']):
            confidence -= 0.15
        
        return min(1.0, max(0.0, confidence))
    
    def get_summary(self, metrics: Dict[str, List[FinancialMetric]]) -> Dict:
        """Create a summary of extracted metrics"""
        summary = {}
        
        for metric_type, metric_list in metrics.items():
            if metric_list:
                # Use highest confidence metric for each type
                best_metric = max(metric_list, key=lambda x: x.confidence)
                summary[metric_type] = {
                    'value': best_metric.value,
                    'unit': best_metric.unit,
                    'confidence': best_metric.confidence,
                    'period': best_metric.period,
                    'count': len(metric_list)
                }
        
        return summary
    
    def to_dict(self, metrics: Dict[str, List[FinancialMetric]]) -> Dict:
        """Convert metrics to dictionary format"""
        return {
            metric_type: [asdict(m) for m in metric_list]
            for metric_type, metric_list in metrics.items()
        }


def extract_financial_metrics(text: str) -> Dict[str, List[FinancialMetric]]:
    """Convenience function to extract metrics"""
    extractor = FinancialMetricExtractor()
    return extractor.extract_metrics(text)


def get_metrics_summary(text: str) -> Dict:
    """Convenience function to get metrics summary"""
    extractor = FinancialMetricExtractor()
    metrics = extractor.extract_metrics(text)
    return extractor.get_summary(metrics)
