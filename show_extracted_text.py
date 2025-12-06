#!/usr/bin/env python3
"""
Display the actual extracted text for each section.
Shows what content is being captured for verification.
"""

import sys
import os
from pathlib import Path

sys.path.append('src')
from src.parsing.section_extractor import SectionExtractor
from src.parsing.report_cleaner import ReportCleaner

def show_extracted_sections(file_path, max_chars_per_section=2000):
    """Display extracted sections with their actual text."""
    print(f"\n{'='*80}")
    print(f"EXTRACTED TEXT FROM: {os.path.basename(file_path)}")
    print('='*80)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        original_text = f.read()
    
    # Extract sections
    extractor = SectionExtractor()
    sections = extractor.extract_sections(original_text)
    
    if not sections:
        print("❌ No sections extracted!")
        return
    
    cleaner = ReportCleaner(remove_boilerplate=True)
    
    # Show each section
    for section_name in sorted(sections.keys()):
        section = sections[section_name]
        
        print(f"\n{'='*80}")
        print(f"SECTION: {section_name} ({section.item_number})")
        print(f"Lines: {section.start_pos} to {section.end_pos}")
        print('='*80)
        
        # Show raw content
        raw_content = section.content
        raw_words = len(raw_content.split())
        print(f"\n📄 RAW CONTENT ({raw_words:,} words):")
        print("-" * 80)
        print(raw_content[:max_chars_per_section])
        if len(raw_content) > max_chars_per_section:
            print(f"\n... [truncated, showing first {max_chars_per_section} chars of {len(raw_content):,} total] ...")
        
        # Show cleaned content
        cleaned_content = cleaner.clean_text(raw_content)
        cleaned_words = len(cleaned_content.split())
        print(f"\n\n🧹 CLEANED CONTENT ({cleaned_words:,} words):")
        print("-" * 80)
        print(cleaned_content[:max_chars_per_section])
        if len(cleaned_content) > max_chars_per_section:
            print(f"\n... [truncated, showing first {max_chars_per_section} chars of {len(cleaned_content):,} total] ...")
        
        print("\n")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Show extracted text from SEC filings')
    parser.add_argument('file', nargs='?', help='File to analyze (default: all files)')
    parser.add_argument('--max-chars', type=int, default=2000, 
                       help='Maximum characters to show per section (default: 2000)')
    parser.add_argument('--section', help='Show only this section (e.g., "MD&A")')
    
    args = parser.parse_args()
    
    if args.file:
        files = [args.file]
    else:
        # Default: show all files in raw directory
        raw_dir = Path('data/raw/earnings_reports')
        files = sorted(raw_dir.glob('*.txt'))
        if not files:
            print("No files found in data/raw/earnings_reports/")
            print("Usage: python show_extracted_text.py <file_path>")
            return
    
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
        
        if args.section:
            # Show only specific section
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            extractor = SectionExtractor()
            sections = extractor.extract_sections(text)
            
            if args.section in sections:
                section = sections[args.section]
                print(f"\n{'='*80}")
                print(f"{args.section} from {os.path.basename(file_path)}")
                print('='*80)
                print(section.content[:args.max_chars])
                if len(section.content) > args.max_chars:
                    print(f"\n... [truncated, showing first {args.max_chars} chars] ...")
            else:
                print(f"Section '{args.section}' not found in {file_path}")
                print(f"Available sections: {', '.join(sections.keys())}")
        else:
            show_extracted_sections(str(file_path), args.max_chars)

if __name__ == '__main__':
    main()

