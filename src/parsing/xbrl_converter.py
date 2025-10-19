#!/usr/bin/env python3
"""
XBRL to Plain Text Converter
Converts XBRL financial data to readable plain text format
"""

import re
import os
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from html_cleaner import clean_html_content


def extract_narrative_sections(file_path):
    """Extract narrative sections from SEC filings for sentiment analysis"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        # Extract the main document content (skip SEC headers)
        if '<DOCUMENT>' in content and '</DOCUMENT>' in content:
            # Extract content between <DOCUMENT> and </DOCUMENT>
            start = content.find('<DOCUMENT>')
            end = content.find('</DOCUMENT>')
            if start != -1 and end != -1:
                content = content[start:end]
        
        # Clean the content
        cleaned_content = clean_html_content(content)
        
        # Split into lines and process
        lines = cleaned_content.split('\n')
        narrative_sections = []
        current_section = []
        in_narrative = False
        
        # Look for key narrative sections
        narrative_keywords = [
            'management\'s discussion',
            'risk factors',
            'business overview',
            'results of operations',
            'liquidity and capital',
            'forward-looking statements',
            'covid-19',
            'pandemic',
            'revenue',
            'earnings',
            'growth',
            'outlook',
            'item 1',
            'item 1a',
            'item 7',
            'item 7a'
        ]
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check if this line starts a narrative section
            if any(keyword in line.lower() for keyword in narrative_keywords):
                # Save previous section if it has content
                if current_section and len(' '.join(current_section)) > 500:
                    section_text = ' '.join(current_section)
                    if len(section_text) > 500:  # Only meaningful sections
                        narrative_sections.append(section_text)
                
                # Start new section
                current_section = [line]
                in_narrative = True
                
            elif in_narrative:
                # Continue building current section
                current_section.append(line)
                
                # Stop if we hit another major section or if section gets too long
                if (len(current_section) > 50 or 
                    any(stop_word in line.lower() for stop_word in ['item ', 'part ', 'exhibit', 'table of contents'])):
                    if len(' '.join(current_section)) > 500:
                        section_text = ' '.join(current_section)
                        narrative_sections.append(section_text)
                    current_section = []
                    in_narrative = False
        
        # Add final section if it exists
        if current_section and len(' '.join(current_section)) > 500:
            section_text = ' '.join(current_section)
            narrative_sections.append(section_text)
        
        # If we didn't find good sections, extract the largest text blocks
        if len(narrative_sections) < 3:
            # Split content into chunks and find the largest meaningful ones
            chunks = re.split(r'\n\s*\n', cleaned_content)
            for chunk in chunks:
                chunk = chunk.strip()
                if len(chunk) > 1000 and any(keyword in chunk.lower() for keyword in [
                    'revenue', 'earnings', 'growth', 'profit', 'loss', 'business', 
                    'company', 'financial', 'results', 'operations'
                ]):
                    narrative_sections.append(chunk)
        
        # Remove duplicates and limit
        unique_sections = []
        seen = set()
        for section in narrative_sections:
            section_hash = hash(section[:200])  # Use first 200 chars as identifier
            if section_hash not in seen:
                seen.add(section_hash)
                unique_sections.append(section)
        
        return unique_sections[:5]  # Limit to 5 best sections
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return []


def clean_financial_data(text):
    """Clean and format financial data"""
    # Remove HTML entities
    text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Clean up currency symbols
    text = re.sub(r'\$\s*', '$', text)
    return text.strip()


def convert_xbrl_to_text(input_file, output_file=None):
    """Convert XBRL file to plain text focusing on narrative sections"""
    if not output_file:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_converted.txt"
    
    print(f"Converting {input_file} to {output_file}...")
    
    # Extract narrative sections for sentiment analysis
    narrative_sections = extract_narrative_sections(input_file)
    
    if not narrative_sections:
        print("No narrative sections found in the file.")
        return
    
    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Financial Narrative Extracted from: {input_file}\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("NARRATIVE SECTIONS FOR SENTIMENT ANALYSIS:\n")
        f.write("=" * 50 + "\n\n")
        
        for i, section in enumerate(narrative_sections, 1):
            f.write(f"Section {i}:\n")
            f.write("-" * 30 + "\n")
            f.write(section + "\n\n")
    
    print(f"Conversion complete! Output saved to: {output_file}")
    print(f"Extracted {len(narrative_sections)} narrative sections.")


def main():
    """Main function to convert XBRL files"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python xbrl_converter.py <input_file> [output_file]")
        print("Example: python xbrl_converter.py data/raw/earnings_reports/0000320193_Apple_Inc._10-K_2015-10-28.txt")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        return
    
    convert_xbrl_to_text(input_file, output_file)


if __name__ == "__main__":
    main()
