"""
Deep Financial Analysis Engine
Uses comprehensive multi-API data aggregation + FinBERT NLP
to generate in-depth company outlook reports
"""

import re
import statistics
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
try:
    import torch
except Exception:
    torch = None
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
except Exception:
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)


class DeepAnalysisEngine:
    """
    Generates comprehensive, multi-page financial analysis reports
    by combining all aggregated data sources with FinBERT NLP analysis
    """

    def __init__(self):
        """Initialize FinBERT model"""
        self.model_name = "ProsusAI/finbert"
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}")
            self.tokenizer = None
            self.model = None

    def generate_deep_analysis(self, ticker: str, aggregated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive analysis report from aggregated data.
        
        Returns a detailed report with sections on:
        - Executive Summary
        - Market Position & Valuation
        - Financial Health
        - Growth Trajectory
        - Risk Assessment
        - Macroeconomic Impact
        - Investment Thesis
        - Forward Outlook & Price Target
        """

        report = {
            "ticker": ticker,
            "generated_at": datetime.now().isoformat(),
            "sections": {}
        }

        # Generate each report section
        report["sections"]["executive_summary"] = self._generate_executive_summary(aggregated_data)
        report["sections"]["market_position"] = self._analyze_market_position(aggregated_data)
        report["sections"]["financial_health"] = self._analyze_financial_health(aggregated_data)
        report["sections"]["growth_trajectory"] = self._analyze_growth(aggregated_data)
        report["sections"]["risk_assessment"] = self._assess_risks(aggregated_data)
        report["sections"]["macro_impact"] = self._analyze_macro_impact(aggregated_data)
        report["sections"]["news_sentiment"] = self._analyze_news_with_finbert(aggregated_data)
        report["sections"]["pos_neg_neutral"] = self._synthesize_pos_neg_neutral(aggregated_data)
        report["sections"]["peer_comparison"] = self._generate_peer_comparison(aggregated_data)
        report["sections"]["investment_thesis"] = self._build_investment_thesis(aggregated_data)
        report["sections"]["forward_outlook"] = self._generate_forward_outlook(aggregated_data)

        return report

    def _build_dynamic_keywords(self, ticker: str, company_profile: Dict[str, Any]) -> List[str]:
        """
        Dynamically build relevance keywords for ANY company based on profile data.
        This works for any ticker without hardcoded mappings.
        
        Extracts:
        - Company name and variations (Inc., Corp., etc.)
        - Industry and sector keywords
        - CEO/leadership names (if available)
        - Key products/services mentioned in description
        """
        keywords = [ticker]
        strong_keywords = set()
        
        # Add company name and common variations
        name = company_profile.get("name", "")
        if name:
            keywords.append(name)
            # Also add name without common suffixes for flexibility
            for suffix in [" Inc.", " Corp.", " Ltd.", " LLC"]:
                if name.endswith(suffix):
                    keywords.append(name.replace(suffix, ""))
            # full company name is a strong keyword
            strong_keywords.add(name.lower())
        
        # Extract industry/sector keywords
        industry = company_profile.get("industry", "")
        sector = company_profile.get("sector", "")
        if industry:
            keywords.extend(industry.split())  # e.g., "Consumer Electronics" → ["Consumer", "Electronics"]
        if sector and sector != industry:
            keywords.extend(sector.split())
        
        # Extract key terms from description (nouns, products, services)
        description = company_profile.get("description", "")
        if description:
            # Extract capitalized phrases (likely proper nouns/product names)
            # Find sequences of capitalized words (e.g., "Apple Pay", "AI Chip", "Cloud Services")
            capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', description[:500])
            keywords.extend(capitalized_phrases[:8])  # Limit to avoid noise
            # treat multi-word capitalized phrases as stronger relevance signals
            for p in capitalized_phrases[:8]:
                if len(p.split()) > 1:
                    strong_keywords.add(p.lower())
        
        # Try to extract CEO/leadership if available
        try:
            ceo = company_profile.get("ceo", "")
            if ceo and len(ceo.split()) <= 3:  # Reasonable name length
                keywords.append(ceo.split()[-1])  # Add last name
        except:
            pass
        
        # Remove duplicates while preserving order, filter short keywords (< 2 chars = noise)
        seen = set()
        unique_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen and len(kw) > 1:
                seen.add(kw_lower)
                unique_keywords.append(kw)
        
        # return keywords with strong keywords attached as attribute via tuple
        # We'll encode as a dict-like return: first element is list, second is set of strong keywords
        return unique_keywords, strong_keywords

    def _synthesize_pos_neg_neutral(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize concise Positives / Negatives / Neutral lists with supporting quotes.

        Uses FinBERT to score candidate sentences drawn from recent news, company description,
        and earnings commentary. Returns top examples per bucket with confidence and source.
        """
        output = {"positives": [], "negatives": [], "neutral": []}

        candidates: List[Dict[str, Any]] = []
        ticker = data.get("ticker", "").upper()
        company_profile = data.get("company_profile", {})
        company_name = company_profile.get("name", "")
        
        # Dynamically build relevance keywords from company profile for ANY ticker
        relevance_keywords, strong_keywords = self._build_dynamic_keywords(ticker, company_profile)

        # 1) News headlines & summaries - filter for ticker-relevant content
        # Expand window and check both headline and summary for relevance
        news_items = data.get("news_sentiment", {}).get("items", [])
        for item in news_items[:50]:
            headline = item.get("headline", "")
            summary = item.get("summary", "") or item.get("summary_text", "")
            # include article body/content when available to improve context for FinBERT
            content = item.get("content") or item.get("article_text") or ""
            # prefer headline + summary, but append a slice of content for context
            text_parts = [p for p in [headline, summary] if p]
            if content:
                text_parts.append(content[:800])
            text = ". ".join(text_parts).strip()

            # Check if headline OR summary OR content contains any relevance keyword
            text_upper = text.upper()
            # Strong relevance: require either ticker, company name, or multi-word product phrases
            ticker_present = bool(ticker and ticker.upper() in text_upper)
            company_present = False
            if company_name:
                company_present = company_name.upper() in text_upper or any(name_variant.upper() in text_upper for name_variant in [company_name])

            strong_match = ticker_present or company_present or any(sk.upper() in text_upper for sk in strong_keywords)

            # Basic match (single-word keywords) is noisy -> only accept if strong_match is false AND source is a filing/company_profile
            src = f"news:{item.get('source', 'unknown')}"
            if src.startswith("news:Yahoo"):
                # For Yahoo require strong match
                is_relevant = bool(strong_match)
            else:
                if strong_match:
                    is_relevant = True
                else:
                    # allow basic single-word keyword only for higher-quality sources (non-Yahoo) as a fallback
                    basic_match = any(kw.upper() in text_upper for kw in relevance_keywords)
                    is_relevant = bool(basic_match)

            if text and is_relevant:
                candidates.append({"text": text, "source": src, "date": item.get("datetime"), "headline": headline})

        # 2) Company description sentences
        desc = data.get("company_profile", {}).get("description", "")
        if desc:
            sentences = re.split(r'(?<=[.!?])\s+', desc)
            for s in sentences[:10]:
                if len(s.strip()) > 20:
                    candidates.append({"text": s.strip(), "source": "company_profile"})

        # 2b) SEC filings: MD&A or Results sections (if available)
        filings = data.get("filings", {}).get("sections", {})
        if filings:
            for sec_name in ("MD&A", "Results of Operations", "Business Overview"):
                sec_text = filings.get(sec_name)
                if sec_text:
                    sents = re.split(r'(?<=[.!?])\s+', sec_text)
                    for s in sents[:12]:
                        if len(s.strip()) > 30:
                            candidates.append({"text": s.strip(), "source": f"filing:{sec_name}"})

        # 3) Earnings commentary (last surprise)
        last_surprise = data.get("earnings_analysis", {}).get("eps_trend", {}).get("last_surprise")
        if last_surprise is not None:
            try:
                surprise_pct = float(last_surprise) * 100
                txt = f"Latest reported EPS surprise of {surprise_pct:.1f}% compared to estimates."
                candidates.append({"text": txt, "source": "earnings"})
            except:
                pass

        # If model not loaded, return lightweight synthesis from counts
        if not self.model or not self.tokenizer:
            summary = data.get("news_sentiment", {}).get("sentiment_summary", {})
            pos = summary.get("positive_count", 0)
            neg = summary.get("negative_count", 0)
            neut = summary.get("neutral_count", 0)
            output["positives"].append({"text": f"{pos} positive news articles in recent window", "source": "news_summary", "confidence": 0.5})
            output["negatives"].append({"text": f"{neg} negative news articles in recent window", "source": "news_summary", "confidence": 0.5})
            output["neutral"].append({"text": f"{neut} neutral news articles in recent window", "source": "news_summary", "confidence": 0.5})
            return output

        # Score candidates with FinBERT and compute impact score
        scored = []
        keywords = ["eps", "earnings", "revenue", "guidance", "margin", "growth", "beat", "miss", "surprise", "forecast", "outlook"]
        
        # Financial red flags that indicate negative news (high confidence - only clear negatives)
        # These are strong signals that should override positive sentiment
        negative_flags = [
            # Executive departures/departures
            "departure", "departures", "executive departure", "cfo resign", "ceo resign",
            "left the company", "departure from", "stepped down",
            # Legal/regulatory issues  
            "lawsuit", "investigation", "fine", "penalty", "antitrust", "bankruptcy",
            # Business contraction
            "restructuring", "downgrade", "bankruptcy", "mass layoff", "layoffs",
            # Safety/product issues
            "safety concern", "recall", "defect"
        ]
        
        # Context-aware filters: if headline contains these, don't mark as negative
        # (e.g., "patent lawsuit against competitors" is good for the company)
        positive_context = [
            " against ", " filed against ", " sues ", " suing "
        ]
        
        # Positive indicators that should boost confidence when FinBERT misses them
        positive_indicators = [
            "gains", "rally", "surge", "surge", "jump", "jump", "soars", "outperform", "beat",
            "upbeat", "optimism", "strong", "excellent", "amazing", "buy", "bullish",
            "reshaped", "momentum", "breakout", "innovation"
        ]

        for c in candidates:
            text = c.get("text", "").strip()[:400]
            if not text or len(text.split()) < 6:
                continue

            # simple quality filters for noisy headlines
            src = c.get("source", "")
            # prefer non-Yahoo short list if possible (Yahoo often returns syndication noise)
            if src.startswith("news:Yahoo") and len(text) < 40:
                continue

            try:
                inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=400)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=1)

                sentiment_idx = torch.argmax(probs, dim=1).item()
                confidence = probs[0, sentiment_idx].item()
                sentiment_map = {0: "negative", 1: "neutral", 2: "positive"}
                sentiment = sentiment_map.get(sentiment_idx, "neutral")
                
                # Check for positive/negative indicators in text
                low_text = text.lower()
                has_negative_flag = any(flag in low_text for flag in negative_flags)
                has_positive_context = any(ctx in low_text for ctx in positive_context)
                has_positive_indicator = any(ind in low_text for ind in positive_indicators)

                # PRIORITY 1: Check for NEGATIVE red flags first (most important)
                # Only override to negative if: flag present AND positive sentiment AND no positive context
                if has_negative_flag and sentiment == "positive" and not has_positive_context:
                    if confidence < 0.85:
                        sentiment = "negative"
                        confidence = min(0.9, confidence * 0.6 + 0.3)

                # SPECIAL CASE: Positive numeric growth signals should not be flipped to negative
                # e.g., "Services grew 15% YoY" or headlines with 'momentum' + percent
                if sentiment == "negative":
                    pct_match = re.search(r"\d+\s*%", low_text)
                    if ("grow" in low_text or "grew" in low_text or "growth" in low_text or "momentum" in low_text or "surge" in low_text) and pct_match and (ticker_present or company_present):
                        sentiment = "positive"
                        confidence = max(confidence, 0.82)

                # PRIORITY 2: Boost positive if indicators present and NOT already flagged as negative
                # This corrects cases like "Nvidia Gains Amid Optimism" scored as negative
                elif has_positive_indicator and sentiment != "positive":
                    if confidence < 0.75:  # Only boost if not too confident in current sentiment
                        sentiment = "positive"
                        confidence = min(0.95, max(0.75, confidence))
                elif has_positive_indicator and sentiment == "positive":
                    # FinBERT got it right, boost the confidence
                    confidence = min(0.95, confidence * 1.2)

                # Keyword boost
                kw_hits = sum(1 for kw in keywords if kw in low_text)

                # Lexical ensemble: simple positive/negative keyword counts to correct low-confidence disagreements
                pos_kw_count = sum(1 for ind in positive_indicators if ind in low_text)
                neg_kw_count = sum(1 for flag in negative_flags if flag in low_text)
                lexical_score = pos_kw_count - neg_kw_count
                # If lexical evidence is present and FinBERT confidence is modest, prefer lexical direction
                # Use a lower threshold for single strong positives (e.g., "momentum", "surge")
                if abs(lexical_score) >= 1 and confidence < 0.75:
                    if lexical_score > 0:
                        sentiment = "positive"
                        confidence = max(confidence, 0.72)
                    else:
                        sentiment = "negative"
                        confidence = max(confidence, 0.72)

                # Source weight: filings > company_profile > news
                if src.startswith("filing:"):
                    source_weight = 1.5
                elif src == "company_profile":
                    source_weight = 1.2
                else:
                    # Penalize low-quality syndication sources (Yahoo) slightly
                    if src.startswith("news:Yahoo") or src == "news:Yahoo":
                        source_weight = 0.8
                    else:
                        source_weight = 1.0

                impact = confidence * source_weight * (1 + 0.1 * kw_hits)

                scored.append({
                    "text": text,
                    "source": src,
                    "date": c.get("date"),
                    "sentiment": sentiment,
                    "confidence": float(confidence),
                    "impact": float(impact),
                    "kw_hits": kw_hits
                })
            except Exception as e:
                logger.debug(f"FinBERT scoring failed for candidate: {e}")

        # Filter out low-confidence / low-impact items (tuned to include more relevant items)
        min_confidence = 0.45
        filtered = [s for s in scored if s.get("confidence", 0) >= min_confidence]

        # If filtered is empty, relax threshold to get more items
        if not filtered:
            min_confidence = 0.25
            filtered = [s for s in scored if s.get("confidence", 0) >= min_confidence]
        
        # If still empty, use all scored
        if not filtered:
            filtered = scored

        # Deduplicate near-duplicate candidate texts to avoid repeated headlines
        unique_filtered = []
        seen_norm = set()
        for s in sorted(filtered, key=lambda x: x.get("impact", 0), reverse=True):
            txt = s.get("text", "")
            # Normalize: lowercase, remove non-word chars, trim to leading 120 chars
            norm = re.sub(r"\W+", " ", txt).strip().lower()[:120]
            if norm in seen_norm:
                continue
            seen_norm.add(norm)
            unique_filtered.append(s)

        # Sort by impact and bucket (after deduplication)
        positives = sorted([s for s in unique_filtered if s["sentiment"] == "positive"], key=lambda x: x.get("impact", 0), reverse=True)[:5]
        negatives = sorted([s for s in unique_filtered if s["sentiment"] == "negative"], key=lambda x: x.get("impact", 0), reverse=True)[:5]
        neutral = sorted([s for s in unique_filtered if s["sentiment"] == "neutral"], key=lambda x: x.get("impact", 0), reverse=True)[:5]

        output["positives"] = positives
        output["negatives"] = negatives
        output["neutral"] = neutral

        return output

    def _generate_peer_comparison(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a simple peer comparison table using normalized peer metrics."""
        peers = data.get("peer_analysis", {})
        normalized = peers.get("peer_metrics_normalized", {}) if peers else {}

        comparison = {"summary": {}, "by_market_cap": [], "by_pe": []}

        if not normalized:
            comparison["summary"] = {"note": "No peer metrics available"}
            return comparison

        # Build sortable lists
        market_caps = []
        pe_ratios = []

        for ticker, m in normalized.items():
            mc = m.get("market_cap")
            pe = m.get("pe_ratio")
            market_caps.append((ticker, mc or 0))
            pe_ratios.append((ticker, pe or float('inf')))

        market_caps_sorted = sorted(market_caps, key=lambda x: x[1], reverse=True)
        pe_sorted = sorted(pe_ratios, key=lambda x: x[1] if x[1] is not None else float('inf'))

        comparison["by_market_cap"] = [{"ticker": t, "market_cap": mc} for t, mc in market_caps_sorted]
        comparison["by_pe"] = [{"ticker": t, "pe_ratio": (None if p == float('inf') else p)} for t, p in pe_sorted]

        # Summary stats (median market cap and PE if available)
        mc_values = [v for _, v in market_caps if v]
        pe_values = [v for _, v in pe_ratios if v and v != float('inf')]
        try:
            comparison["summary"] = {
                "median_market_cap": statistics.median(mc_values) if mc_values else None,
                "median_pe": statistics.median(pe_values) if pe_values else None,
                "peer_count": len(normalized)
            }
        except Exception:
            comparison["summary"] = {"peer_count": len(normalized)}

        return comparison

    def _generate_executive_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary from aggregated data"""
        summary = {
            "company_name": data.get("company_profile", {}).get("name", "N/A"),
            "industry": data.get("company_profile", {}).get("industry", "N/A"),
            "current_position": self._assess_current_position(data),
            "key_metrics": self._extract_key_metrics(data),
            "headline": ""
        }

        # Generate headline based on overall assessment
        market_data = data.get("market_data", {})
        fundamentals = data.get("fundamentals", {})
        sentiment = data.get("news_sentiment", {}).get("sentiment_summary", {})

        position = summary["current_position"]
        sentiment_trend = sentiment.get("sentiment_trend", "neutral")

        if position == "strong" and sentiment_trend == "positive":
            summary["headline"] = "Strong fundamentals with positive momentum"
        elif position == "weak" and sentiment_trend == "negative":
            summary["headline"] = "Deteriorating fundamentals with negative sentiment"
        elif position == "strong":
            summary["headline"] = "Solid fundamentals but watch sentiment"
        else:
            summary["headline"] = "Mixed signals - detailed analysis required"

        return summary

    def _assess_current_position(self, data: Dict[str, Any]) -> str:
        """Assess company's current market position (strong/moderate/weak)"""
        score = 0
        max_score = 0

        # Check profitability
        fundamentals = data.get("fundamentals", {})
        income = fundamentals.get("income_statement", {})
        if income.get("net_income") and float(income.get("net_income", 0)) > 0:
            score += 2
        max_score += 2

        # Check valuation (PE ratio)
        market_data = data.get("market_data", {})
        overview = market_data.get("company_overview", {})
        pe = overview.get("pe_ratio")
        if pe and float(pe) < 30:
            score += 2
        max_score += 2

        # Check debt levels
        balance_sheet = fundamentals.get("balance_sheet", {})
        if balance_sheet.get("total_equity") and balance_sheet.get("total_liabilities"):
            debt_to_equity = float(balance_sheet.get("total_liabilities", 1)) / float(balance_sheet.get("total_equity", 1))
            if debt_to_equity < 2:
                score += 2
        max_score += 2

        # Check news sentiment
        sentiment = data.get("news_sentiment", {}).get("sentiment_summary", {})
        if sentiment.get("sentiment_trend") == "positive":
            score += 1
        max_score += 1

        # Convert to assessment
        ratio = score / max_score if max_score > 0 else 0.5
        if ratio > 0.7:
            return "strong"
        elif ratio > 0.4:
            return "moderate"
        else:
            return "weak"

    def _extract_key_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the most important financial metrics"""
        metrics = {}

        market_data = data.get("market_data", {})
        overview = market_data.get("company_overview", {})
        
        metrics["market_cap"] = overview.get("market_cap", "N/A")
        metrics["pe_ratio"] = overview.get("pe_ratio", "N/A")
        metrics["eps"] = overview.get("eps", "N/A")
        metrics["revenue"] = overview.get("revenue", "N/A")
        metrics["profit_margin"] = overview.get("profit_margin", "N/A")
        metrics["beta"] = overview.get("beta", "N/A")

        return metrics

    def _analyze_market_position(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze company's competitive market position"""
        analysis = {
            "valuation": "",
            "momentum": "",
            "relative_strength": "",
            "details": {}
        }

        market_data = data.get("market_data", {})
        overview = market_data.get("company_overview", {})
        technicals = data.get("technical_analysis", {})

        # Valuation analysis
        pe = overview.get("pe_ratio")
        if pe:
            try:
                pe_float = float(pe)
                if pe_float < 15:
                    analysis["valuation"] = "Undervalued - Trading at discount to market"
                elif pe_float < 25:
                    analysis["valuation"] = "Fairly valued - Inline with market average"
                else:
                    analysis["valuation"] = "Premium valuation - Higher growth expectations priced in"
            except:
                analysis["valuation"] = "Unable to assess"

        # Momentum analysis
        momentum = technicals.get("20_day_momentum")
        if momentum is not None:
            try:
                momentum_pct = float(momentum) * 100
                if momentum_pct > 5:
                    analysis["momentum"] = f"Positive momentum - Stock up {momentum_pct:.1f}% over 20 days"
                elif momentum_pct < -5:
                    analysis["momentum"] = f"Negative momentum - Stock down {abs(momentum_pct):.1f}% over 20 days"
                else:
                    analysis["momentum"] = "Neutral momentum - Consolidating recent gains"
            except:
                analysis["momentum"] = "Unable to assess"

        # Peer comparison
        peers = data.get("peer_analysis", {}).get("peer_tickers", [])
        analysis["details"]["peer_count"] = len(peers)
        analysis["details"]["peers"] = peers

        return analysis

    def _analyze_financial_health(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze company's financial health and stability"""
        health = {
            "overall_rating": "Moderate",
            "profitability": "",
            "liquidity": "",
            "leverage": "",
            "details": {}
        }

        fundamentals = data.get("fundamentals", {})
        income = fundamentals.get("income_statement", {})
        balance = fundamentals.get("balance_sheet", {})
        market = data.get("market_data", {})
        
        # Extract nested market data
        company_overview = market.get("company_overview", {})
        yahoo_info = market.get("yahoo_info", {})

        # Profitability - try multiple sources
        profit_margin = company_overview.get("profit_margin") or yahoo_info.get("roe")
        
        if profit_margin:
            try:
                margin = float(profit_margin)
                if margin < 1:
                    margin = margin * 100  # Convert if in decimal form
                if margin > 20:
                    health["profitability"] = f"Excellent - {margin:.1f}% margin"
                elif margin > 10:
                    health["profitability"] = f"Good - {margin:.1f}% margin"
                elif margin > 5:
                    health["profitability"] = f"Moderate - {margin:.1f}% margin"
                else:
                    health["profitability"] = f"Concerning - {margin:.1f}% margin"
            except:
                pass

        # Alternative profitability calculation from income statement
        if not health.get("profitability") and income.get("net_income") and income.get("revenue"):
            try:
                net_income = float(income.get("net_income", 0))
                revenue = float(income.get("revenue", 1))
                margin = (net_income / revenue) * 100 if revenue > 0 else 0
                if margin > 15:
                    health["profitability"] = f"Excellent - {margin:.1f}% net margin"
                elif margin > 5:
                    health["profitability"] = f"Good - {margin:.1f}% net margin"
                else:
                    health["profitability"] = f"Concerning - {margin:.1f}% net margin"
            except:
                pass

        if not health.get("profitability"):
            health["profitability"] = "Unable to assess (data unavailable)"

        # Liquidity - cash position or current ratio
        cash = balance.get("cash")
        current_ratio = yahoo_info.get("current_ratio")
        
        if cash:
            try:
                cash_float = float(cash)
                health["liquidity"] = f"Cash position: ${cash_float/1e9:.1f}B available"
            except:
                pass
        elif current_ratio:
            try:
                cr = float(current_ratio)
                if cr > 1.5:
                    health["liquidity"] = f"Strong liquidity - Current ratio {cr:.2f}"
                elif cr > 1:
                    health["liquidity"] = f"Adequate liquidity - Current ratio {cr:.2f}"
                else:
                    health["liquidity"] = f"Tight liquidity - Current ratio {cr:.2f}"
            except:
                pass

        # Leverage - debt to equity
        debt_to_equity = yahoo_info.get("debt_to_equity")
        
        if balance.get("total_equity") and balance.get("total_liabilities"):
            try:
                de = float(balance.get("total_liabilities", 0)) / float(balance.get("total_equity", 1))
                if de < 1:
                    health["leverage"] = f"Conservative - D/E ratio {de:.2f}"
                elif de < 2:
                    health["leverage"] = f"Moderate - D/E ratio {de:.2f}"
                else:
                    health["leverage"] = f"High - D/E ratio {de:.2f}"
            except:
                pass
        elif debt_to_equity:
            try:
                de = float(debt_to_equity)
                if de < 1:
                    health["leverage"] = f"Conservative - D/E ratio {de:.2f}"
                elif de < 2:
                    health["leverage"] = f"Moderate - D/E ratio {de:.2f}"
                else:
                    health["leverage"] = f"High - D/E ratio {de:.2f}"
            except:
                pass

        if not health.get("leverage"):
            health["leverage"] = "Unable to assess (data unavailable)"

        return health

    def _analyze_growth(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze company's growth trajectory and trends"""
        growth = {
            "eps_trend": "",
            "revenue_trend": "",
            "growth_rating": "",
            "details": {}
        }

        earnings = data.get("earnings_analysis", {})
        market = data.get("market_data", {})
        overview = market.get("company_overview", {})
        
        eps_trend = earnings.get("eps_trend", {})
        eps_growth = market.get("eps_growth")
        revenue_growth = market.get("revenue_growth")

        # EPS Trend from earnings data
        if eps_trend.get("beat_rate") is not None:
            beat_rate = float(eps_trend.get("beat_rate", 0)) * 100
            if beat_rate > 75:
                growth["eps_trend"] = f"Excellent - Company beats estimates {beat_rate:.0f}% of the time"
            elif beat_rate > 50:
                growth["eps_trend"] = f"Good - Company beats estimates {beat_rate:.0f}% of the time"
            else:
                growth["eps_trend"] = f"Below average - Company beats estimates only {beat_rate:.0f}% of the time"
        
        # Alternative: EPS growth from market data
        if not growth.get("eps_trend") and eps_growth:
            try:
                eps_growth_float = float(eps_growth)
                if eps_growth_float > 15:
                    growth["eps_trend"] = f"Strong - EPS growing at {eps_growth_float:.1f}% annually"
                elif eps_growth_float > 5:
                    growth["eps_trend"] = f"Moderate - EPS growing at {eps_growth_float:.1f}% annually"
                else:
                    growth["eps_trend"] = f"Marginal - EPS growing at {eps_growth_float:.1f}% annually"
            except:
                pass

        # Fallback: Try to calculate EPS growth from current EPS if available
        if not growth.get("eps_trend"):
            current_eps = overview.get("eps")
            if current_eps:
                try:
                    eps_val = float(current_eps)
                    if eps_val > 5:
                        growth["eps_trend"] = f"Marginal - Current EPS of ${eps_val:.2f} shows thin margins"
                    else:
                        growth["eps_trend"] = f"Marginal - Current EPS of ${eps_val:.2f} indicates profitability"
                except:
                    pass

        if not growth.get("eps_trend"):
            growth["eps_trend"] = "Growth metrics not available"

        # Revenue growth
        if revenue_growth:
            try:
                rev_growth_float = float(revenue_growth)
                if rev_growth_float > 15:
                    growth["revenue_trend"] = f"Strong revenue expansion at {rev_growth_float:.1f}% annually"
                elif rev_growth_float > 5:
                    growth["revenue_trend"] = f"Steady revenue growth at {rev_growth_float:.1f}% annually"
                else:
                    growth["revenue_trend"] = f"Slowing growth at {rev_growth_float:.1f}% annually"
            except:
                pass

        if not growth.get("revenue_trend"):
            growth["revenue_trend"] = "Revenue growth data not available"

        return growth

    def _assess_risks(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Identify key risks to investment thesis"""
        risks = {
            "high_risk_factors": [],
            "medium_risk_factors": [],
            "risk_score": 0
        }

        fundamentals = data.get("fundamentals", {})
        balance = fundamentals.get("balance_sheet", {})
        market = data.get("market_data", {})
        sentiment = data.get("news_sentiment", {}).get("sentiment_summary", {})
        macro = data.get("macroeconomic_context", {})
        profile = data.get("company_profile", {})
        
        # Extract nested market data
        company_overview = market.get("company_overview", {})
        yahoo_info = market.get("yahoo_info", {})

        # Check leverage risk
        if balance.get("total_equity") and balance.get("total_liabilities"):
            try:
                de = float(balance.get("total_liabilities", 0)) / float(balance.get("total_equity", 1))
                if de > 3:
                    risks["high_risk_factors"].append(f"High leverage - Debt-to-Equity ratio {de:.1f}")
            except:
                pass

        # Check price volatility (Beta)
        beta = company_overview.get("beta")
        if beta:
            try:
                beta_float = float(beta)
                if beta_float > 2:
                    risks["medium_risk_factors"].append(f"Elevated volatility - Beta of {beta_float:.2f} above market average")
            except:
                pass

        # Check sentiment risk
        if sentiment.get("negative_count", 0) > sentiment.get("positive_count", 0):
            risks["medium_risk_factors"].append("Negative news sentiment outweighs positive coverage")

        # Check valuation risk - try multiple sources
        pe_ratio = company_overview.get("pe_ratio") or yahoo_info.get("trailing_pe")
        if pe_ratio:
            try:
                pe_float = float(pe_ratio)
                if pe_float > 50:
                    risks["medium_risk_factors"].append(f"Premium valuation - P/E ratio of {pe_float:.1f} suggests high expectations priced in")
            except:
                pass

        # Check macro risks
        unemployment = macro.get("unemployment_rate")
        if unemployment:
            try:
                unemployment_float = float(unemployment)
                if unemployment_float > 5:
                    risks["medium_risk_factors"].append(f"Rising unemployment ({unemployment_float:.1f}%) may impact consumer spending")
            except:
                pass

        # Check interest rate environment
        interest_rate = macro.get("interest_rate")
        if interest_rate:
            try:
                rate_float = float(interest_rate)
                if rate_float > 4:
                    risks["medium_risk_factors"].append(f"Higher interest rates ({rate_float:.2f}%) increase cost of capital")
            except:
                pass

        risks["risk_score"] = len(risks["high_risk_factors"]) * 3 + len(risks["medium_risk_factors"])

        return risks

    def _analyze_macro_impact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze macroeconomic impact on the company"""
        macro_impact = {
            "economic_environment": "",
            "relevant_indicators": {},
            "industry_implications": ""
        }

        macro = data.get("macroeconomic_context", {})

        # GDP impact
        if macro.get("gdp_growth"):
            try:
                gdp = float(macro.get("gdp_growth"))
                if gdp > 3:
                    macro_impact["economic_environment"] = f"Strong economic growth ({gdp:.1f}%)"
                elif gdp > 1:
                    macro_impact["economic_environment"] = f"Moderate growth ({gdp:.1f}%)"
                else:
                    macro_impact["economic_environment"] = f"Slowing growth ({gdp:.1f}%)"
            except:
                pass

        macro_impact["relevant_indicators"] = macro

        return macro_impact

    def _build_investment_thesis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive investment thesis with dynamic conviction scoring"""
        thesis = {
            "bull_case": "",
            "bear_case": "",
            "conviction_level": "Medium"
        }

        position = self._assess_current_position(data)
        sentiment = data.get("news_sentiment", {}).get("sentiment_summary", {}).get("sentiment_trend")
        
        # Build conviction score from multiple factors
        conviction_score = 0.5  # Start at neutral
        
        # Position assessment (0-1)
        if position == "strong":
            conviction_score += 0.25
        elif position == "weak":
            conviction_score -= 0.25
        
        # News sentiment (0-1)
        if sentiment == "positive":
            conviction_score += 0.15
        elif sentiment == "negative":
            conviction_score -= 0.15
        
        # Valuation check (0-1)
        market = data.get("market_data", {})
        overview = market.get("company_overview", {})
        try:
            pe = float(overview.get("pe_ratio", 0))
            if pe < 12:
                conviction_score += 0.1
            elif pe > 30:
                conviction_score -= 0.1
        except:
            pass
        
        # Growth trajectory check (0-1)
        growth = data.get("growth_trajectory", {})
        eps_trend = growth.get("eps_trend", "")
        if "strong" in eps_trend.lower() or "excellent" in eps_trend.lower():
            conviction_score += 0.15
        elif "declining" in eps_trend.lower() or "miss" in eps_trend.lower():
            conviction_score -= 0.15
        
        # Convert score to conviction level
        if conviction_score >= 0.65:
            thesis["conviction_level"] = "High"
        elif conviction_score >= 0.35:
            thesis["conviction_level"] = "Medium"
        else:
            thesis["conviction_level"] = "Low"

        return thesis

    def _generate_forward_outlook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate forward-looking outlook and price targets"""
        outlook = {
            "outlook_summary": "",
            "price_target_12m": "N/A",
            "upside_downside": "N/A",
            "key_catalysts": [],
            "next_milestones": []
        }

        market_data = data.get("market_data", {})
        overview = market_data.get("company_overview", {})
        earnings = data.get("earnings_analysis", {})

        current_price = market_data.get("realtime_quote", {}).get("current_price")
        if current_price:
            try:
                cp = float(current_price)
                pe = float(overview.get("pe_ratio", 20))
                eps = float(overview.get("eps", 1))
                # Simple target: 5% upside if fair valued
                target = cp * 1.05
                outlook["price_target_12m"] = f"${target:.2f}"
                upside = ((target - cp) / cp) * 100
                outlook["upside_downside"] = f"{upside:.1f}%"
            except:
                pass

        # Key catalysts
        calendar = earnings.get("calendar", [])
        if calendar:
            outlook["key_catalysts"] = calendar[:3]

        outlook["outlook_summary"] = "Continue to monitor quarterly results and market conditions for validation of thesis"

        return outlook

    def _analyze_news_with_finbert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze recent news items using FinBERT for detailed sentiment"""
        analysis = {
            "finbert_sentiment": "",
            "top_news_items": [],
            "sentiment_score": 0.5
        }

        news_items = data.get("news_sentiment", {}).get("items", [])
        
        if not news_items or not self.model:
            analysis["finbert_sentiment"] = "News analysis not available"
            return analysis

        # Analyze top 5 recent news items
        sentiment_scores = []
        
        for item in news_items[:5]:
            headline = item.get("headline", "")
            if not headline:
                continue
            
            try:
                inputs = self.tokenizer(headline, return_tensors="pt", truncation=True, max_length=512)
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=1)
                
                sentiment_idx = torch.argmax(probs, dim=1).item()
                confidence = probs[0, sentiment_idx].item()
                sentiment_map = {0: "negative", 1: "neutral", 2: "positive"}
                sentiment = sentiment_map.get(sentiment_idx, "neutral")
                
                sentiment_scores.append(confidence if sentiment == "positive" else -confidence)
                analysis["top_news_items"].append({
                    "headline": headline,
                    "sentiment": sentiment,
                    "finbert_sentiment": sentiment,
                    "confidence": float(confidence)
                })
            except Exception:
                pass
        
        # Calculate average sentiment
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            analysis["sentiment_score"] = float(avg_sentiment)
            if avg_sentiment > 0.1:
                analysis["finbert_sentiment"] = "Positive sentiment dominates"
            elif avg_sentiment < -0.1:
                analysis["finbert_sentiment"] = "Negative sentiment dominates"
            else:
                analysis["finbert_sentiment"] = "Mixed sentiment"
        else:
            analysis["finbert_sentiment"] = "Insufficient data for analysis"

        return analysis


def generate_deep_analysis_report(ticker: str, aggregated_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate full deep analysis report"""
    engine = DeepAnalysisEngine()
    return engine.generate_deep_analysis(ticker, aggregated_data)
