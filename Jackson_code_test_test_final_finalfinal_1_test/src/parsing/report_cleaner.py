"""
Utility to clean SEC filings (8-K, 10-K, 10-Q) by removing neutral boilerplate
and extracting sentiment-bearing content for FinBERT analysis.
"""

import re
from typing import List, Tuple


class ReportCleaner:
    """Cleans financial reports by removing neutral boilerplate and extracting meaningful content."""
    
    # Patterns to identify and remove boilerplate sections
    BOILERPLATE_PATTERNS = [
        # Legal disclaimers
        r"Pursuant to the requirements of.*?Exchange Act",
        r"Securities Exchange Act of 1934",
        r"17 CFR \d+\.\d+",
        r"Rule \d+",
        r"Section \d+",
        r"Regulation \w+",
        r"§\d+\.\d+",
        
        # Form headers and administrative
        r"UNITED STATES\s*SECURITIES AND EXCHANGE COMMISSION",
        r"FORM \d+-[KQ]",
        r"ANNUAL REPORT PURSUANT TO",
        r"QUARTERLY REPORT PURSUANT TO",
        r"CURRENT REPORT",
        r"Commission file number:",
        r"State or other jurisdiction",
        r"IRS Employer.*?Identification No",
        r"Address of principal executive offices",
        r"Registrant's telephone number",
        r"Securities registered pursuant to",
        r"Trading Symbol\(s\)",
        r"Name of each exchange",
        r"Indicate by check mark",
        r"Yes ☐ No ☐",
        r"☐",
        r"Emerging Growth Company",
        r"Large accelerated filer",
        r"Accelerated filer",
        r"Non-accelerated filer",
        r"SIGNATURE",
        r"Pursuant to the requirements",
        r"duly caused this report to be signed",
        r"By: /s/",
        
        # Table of contents
        r"Table of Contents",
        r"Item \d+\.",
        r"Part [IVX]+",
        
        # Forward-looking disclaimers (keep structure but can filter if too verbose)
        r"Forward-Looking Statements",
        r"may cause our actual results.*?to be materially different",
        r"you should not place undue reliance",
        r"Except as required by law",
        
        # Incorporation by reference
        r"incorporated by reference",
        r"incorporated herein by reference",
        r"DOCUMENTS INCORPORATED BY REFERENCE",
        
        # Social media and website references
        r"https?://[^\s]+",
        r"investor relations website",
        r"social media channels",
        
        # Copyright and legal notices
        r"© \d+.*?All rights reserved",
        r"All references to.*?mean.*?and its subsidiaries",
    ]
    
    # Sections that typically contain sentiment-bearing content
    SENTIMENT_SECTIONS = [
        r"Item \d+\.\d+.*?Results of Operations",
        r"Management's Discussion and Analysis",
        r"MD&A",
        r"Results of Operations",
        r"Financial Condition",
        r"Press Release",
        r"CFO Commentary",
        r"Executive Summary",
        r"Business Overview",
        r"Highlights",
        r"Financial Highlights",
        r"Quarterly Results",
        r"Annual Results",
    ]
    
    # Phrases that indicate neutral/boilerplate content
    NEUTRAL_PHRASES = [
        "not applicable",
        "none",
        "n/a",
        "see above",
        "see below",
        "incorporated by reference",
        "furnished and shall not be deemed",
        "shall not be incorporated by reference",
        "subject to the liabilities",
    ]
    
    # Common filler/stop words that don't add financial meaning (remove from sentences)
    # These are removed to reduce noise without cutting content
    FILLER_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'being', 'have',
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
        'might', 'must', 'can', 'this', 'that', 'these', 'those', 'it', 'its', 'they',
        'them', 'their', 'there', 'here', 'where', 'when', 'what', 'which', 'who',
        'whom', 'whose', 'how', 'why', 'if', 'then', 'than', 'so', 'such', 'very',
        'more', 'most', 'much', 'many', 'some', 'any', 'all', 'each', 'every', 'both',
        'other', 'another', 'same', 'different', 'own', 'just', 'only', 'also', 'too',
        'even', 'still', 'yet', 'already', 'again', 'once', 'twice', 'always', 'never',
        'often', 'sometimes', 'usually', 'generally', 'specifically', 'particularly',
        'especially', 'mainly', 'mostly', 'primarily', 'essentially', 'basically',
        'actually', 'really', 'quite', 'rather', 'fairly', 'pretty', 'somewhat',
        'approximately', 'about', 'around', 'nearly', 'almost', 'exactly', 'precisely',
    }
    
    # Legal/filler phrases to remove (keep structure but remove noise)
    LEGAL_FILLER_PHRASES = [
        r'\bthe\s+company\b',  # Too generic, context usually clear
        r'\bwe\s+believe\b',  # Legal hedging, not sentiment
        r'\bwe\s+expect\b',  # Forward-looking, often neutral
        r'\bmay\s+result\s+in\b',
        r'\bcould\s+result\s+in\b',
        r'\bwould\s+result\s+in\b',
        r'\bsubject\s+to\b',
        r'\bconsistent\s+with\b',
        r'\bin\s+accordance\s+with\b',
        r'\bpursuant\s+to\b',
    ]
    
    def __init__(self, 
                 remove_boilerplate: bool = True,
                 extract_sections_only: bool = False,
                 min_sentence_length: int = 20,
                 remove_short_paragraphs: bool = True):
        """
        Initialize the ReportCleaner.
        
        Args:
            remove_boilerplate: Remove identified boilerplate patterns
            extract_sections_only: Only extract sentiment-bearing sections
            min_sentence_length: Minimum characters for a sentence to be kept
            remove_short_paragraphs: Remove paragraphs shorter than threshold
        """
        self.remove_boilerplate = remove_boilerplate
        self.extract_sections_only = extract_sections_only
        self.min_sentence_length = min_sentence_length
        self.remove_short_paragraphs = remove_short_paragraphs
    
    def clean_text(self, text: str) -> str:
        """
        Clean financial report text by removing boilerplate.
        
        Args:
            text: Raw report text
            
        Returns:
            Cleaned text with neutral content removed
        """
        if self.extract_sections_only:
            text = self._extract_sentiment_sections(text)
        
        if self.remove_boilerplate:
            text = self._remove_boilerplate_patterns(text)
        
        text = self._clean_formatting(text)
        text = self._remove_neutral_phrases(text)
        
        if self.remove_short_paragraphs:
            text = self._remove_short_content(text)
        
        return text.strip()
    
    def _extract_sentiment_sections(self, text: str) -> str:
        """Extract only sections that likely contain sentiment."""
        sections = []
        lines = text.split('\n')
        in_sentiment_section = False
        current_section = []
        
        for line in lines:
            # Check if line starts a sentiment section
            for pattern in self.SENTIMENT_SECTIONS:
                if re.search(pattern, line, re.IGNORECASE):
                    if current_section:
                        sections.append('\n'.join(current_section))
                    current_section = [line]
                    in_sentiment_section = True
                    break
            else:
                if in_sentiment_section:
                    # Check if we hit a new major section (Item X.)
                    if re.match(r'^Item \d+\.', line):
                        if current_section:
                            sections.append('\n'.join(current_section))
                        current_section = []
                        in_sentiment_section = False
                    else:
                        current_section.append(line)
        
        if current_section:
            sections.append('\n'.join(current_section))
        
        return '\n\n'.join(sections) if sections else text
    
    def _remove_boilerplate_patterns(self, text: str) -> str:
        """Remove identified boilerplate patterns."""
        for pattern in self.BOILERPLATE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        return text
    
    def _clean_formatting(self, text: str) -> str:
        """Clean up formatting issues."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove lines that are just punctuation or symbols
        text = re.sub(r'^[^\w\s]+$', '', text, flags=re.MULTILINE)
        return text.strip()
    
    def _remove_neutral_phrases(self, text: str) -> str:
        """
        Remove neutral phrases and redundant content to shorten text while preserving sentiment.
        More aggressive than before - removes repetitive and low-value sentences.
        """
        # Split into sentences
        sentences = re.split(r'[.!?]\s+', text)
        filtered_sentences = []
        seen_sentences = set()  # Track duplicates
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:  # Skip very short fragments
                continue
            
            sentence_lower = sentence.lower()
            
            # Skip duplicates (normalized)
            sentence_normalized = re.sub(r'[^\w\s]', '', sentence_lower)
            if sentence_normalized in seen_sentences:
                continue
            seen_sentences.add(sentence_normalized)
            
            # Skip if sentence is purely neutral boilerplate (no financial content)
            if any(phrase in sentence_lower for phrase in self.NEUTRAL_PHRASES):
                # Check if it has any financial/business content
                has_financial_content = re.search(
                    r'\b(revenue|earnings|profit|loss|growth|decline|increase|decrease|margin|EPS|guidance|sales|income|expense|cash|debt|equity|assets|liabilities|operating|net|gross|business|company|quarter|year|period|results|performance|financial|market|customer|product|service|demand|supply|pricing|cost|risk|challenge|opportunity|strategy|competitive|market share|acquisition|partnership|investment|capital|revenue|expense)\b',
                    sentence_lower
                )
                if not has_financial_content:
                    continue  # Skip pure boilerplate
            
            # Skip if sentence is mostly legal citations
            if re.search(r'\d+\s+CFR|\d+\.\d+\)|Rule\s+\d+|Section\s+\d+', sentence):
                citation_count = len(re.findall(r'\d+', sentence))
                if citation_count > 3 and len(sentence.split()) < 15:  # Mostly citations
                    continue
            
            # Skip sentences that are just references to other sections
            if re.search(r'^refer to|^see |^see item|^see part |^see note \d+', sentence_lower):
                if len(sentence.split()) < 10:  # Short reference sentences
                    continue
            
            # Skip sentences that are just formatting/structural
            if re.match(r'^(table|figure|exhibit|note|item)\s+\d+', sentence_lower):
                if len(sentence.split()) < 5:
                    continue
            
            # Keep the sentence
            filtered_sentences.append(sentence)
        
        return '. '.join(filtered_sentences)
    
    def _remove_short_content(self, text: str) -> str:
        """Remove paragraphs and sentences that are too short."""
        paragraphs = text.split('\n\n')
        filtered_paragraphs = []
        
        for para in paragraphs:
            para = para.strip()
            # Keep if paragraph is substantial
            if len(para) >= 50:
                filtered_paragraphs.append(para)
            # Or if it contains financial keywords
            elif re.search(r'\b(revenue|earnings|profit|loss|growth|decline|increase|decrease|margin|EPS|guidance)\b', 
                          para, re.IGNORECASE):
                filtered_paragraphs.append(para)
        
        return '\n\n'.join(filtered_paragraphs)
    
    def extract_sentences(self, text: str, min_length: int = 30) -> List[str]:
        """
        Extract individual sentences from cleaned text for sentence-level analysis.
        
        Args:
            text: Cleaned report text
            min_length: Minimum sentence length
            
        Returns:
            List of sentences
        """
        cleaned = self.clean_text(text)
        sentences = re.split(r'[.!?]\s+', cleaned)
        
        filtered = []
        for sent in sentences:
            sent = sent.strip()
            if len(sent) >= min_length:
                # Filter out sentences that are likely still boilerplate
                if not any(phrase in sent.lower() for phrase in self.NEUTRAL_PHRASES):
                    filtered.append(sent)
        
        return filtered
    
    def get_sentiment_segments(self, text: str, max_length: int = 512) -> List[str]:
        """
        Split cleaned text into segments suitable for FinBERT (max token length).
        
        Args:
            text: Cleaned report text
            max_length: Maximum characters per segment
            
        Returns:
            List of text segments
        """
        cleaned = self.clean_text(text)
        sentences = self.extract_sentences(cleaned)
        
        segments = []
        current_segment = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            if current_length + sentence_length > max_length and current_segment:
                segments.append(' '.join(current_segment))
                current_segment = [sentence]
                current_length = sentence_length
            else:
                current_segment.append(sentence)
                current_length += sentence_length + 1  # +1 for space
        
        if current_segment:
            segments.append(' '.join(current_segment))
        
        return segments


def clean_report_file(input_path: str, output_path: str = None, 
                     extract_sections_only: bool = True, auto_save: bool = False) -> str:
    """
    Convenience function to clean a report file.
    
    Args:
        input_path: Path to input file
        output_path: Path to save cleaned file (if None and auto_save=True, auto-generates path in data/processed/)
        extract_sections_only: Only extract sentiment sections
        auto_save: If True and output_path is None, auto-generate path in processed directory
        
    Returns:
        Cleaned text or path to saved file
    """
    import os
    
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    cleaner = ReportCleaner(extract_sections_only=extract_sections_only)
    cleaned = cleaner.clean_text(text)
    
    # Auto-generate processed path if requested
    if output_path is None and auto_save:
        # Convert raw path to processed path
        # e.g., data/raw/earnings_reports/file.txt -> data/processed/earnings_reports/file_cleaned.txt
        processed_path = input_path.replace('data/raw/', 'data/processed/')
        processed_dir = os.path.dirname(processed_path)
        os.makedirs(processed_dir, exist_ok=True)
        
        # Add _cleaned suffix before extension
        base, ext = os.path.splitext(processed_path)
        output_path = f"{base}_cleaned{ext}"
    
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)
        return output_path
    else:
        return cleaned

