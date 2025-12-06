"""
Example script showing how to use ReportCleaner to clean SEC filings
before sentiment analysis with FinBERT.
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.parsing.report_cleaner import ReportCleaner, clean_report_file

def main():
    # Example 1: Clean a single file (with explicit output path)
    input_file = "data/raw/earnings_reports/NVDA_8-K_1.txt"
    output_file = "data/processed/earnings_reports/NVDA_8-K_1_cleaned.txt"
    
    if os.path.exists(input_file):
        print(f"Cleaning {input_file}...")
        clean_report_file(input_file, output_file, extract_sections_only=True)
        print(f"Cleaned file saved to {output_file}")
        
        # Alternative: Use auto_save to automatically generate processed path
        # clean_report_file(input_file, auto_save=True, extract_sections_only=True)
        
        # Show comparison
        with open(input_file, 'r') as f:
            original = f.read()
        with open(output_file, 'r') as f:
            cleaned = f.read()
        
        print(f"\nOriginal length: {len(original)} characters")
        print(f"Cleaned length: {len(cleaned)} characters")
        print(f"Reduction: {100 * (1 - len(cleaned)/len(original)):.1f}%")
        print(f"\nCleaned text preview:\n{cleaned[:500]}...")
    
    # Example 2: Use cleaner programmatically
    print("\n" + "="*60)
    print("Example 2: Programmatic usage")
    print("="*60)
    
    cleaner = ReportCleaner(
        extract_sections_only=True,  # Only extract sentiment sections
        remove_boilerplate=True,     # Remove legal boilerplate
        min_sentence_length=30,      # Minimum sentence length
        remove_short_paragraphs=True  # Remove very short paragraphs
    )
    
    sample_text = """
    UNITED STATES SECURITIES AND EXCHANGE COMMISSION
    FORM 8-K CURRENT REPORT
    Pursuant to Section 13 or 15(d) of the Securities Exchange Act of 1934
    
    Item 2.02 Results of Operations and Financial Condition.
    On August 27, 2025, NVIDIA Corporation announced its results for the quarter.
    Revenue increased 50% year-over-year to $15 billion, driven by strong demand
    for AI chips. Earnings per share grew 60% compared to the prior year.
    The company expects continued growth in the next quarter.
    
    SIGNATURE
    Pursuant to the requirements of the Securities Exchange Act of 1934...
    """
    
    cleaned = cleaner.clean_text(sample_text)
    print(f"\nOriginal:\n{sample_text}")
    print(f"\nCleaned:\n{cleaned}")
    
    # Example 3: Extract sentences for sentence-level analysis
    print("\n" + "="*60)
    print("Example 3: Sentence extraction")
    print("="*60)
    
    sentences = cleaner.extract_sentences(sample_text)
    print(f"\nExtracted {len(sentences)} sentences:")
    for i, sent in enumerate(sentences, 1):
        print(f"{i}. {sent}")

if __name__ == "__main__":
    main()

