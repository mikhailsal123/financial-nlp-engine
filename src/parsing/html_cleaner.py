#!/usr/bin/env python3
"""
HTML Cleaner for Financial Documents
Removes HTML tags, styling, and formatting to extract clean text
"""

import re
import os
from bs4 import BeautifulSoup


def clean_html_content(html_text):
    """
    Clean HTML content and extract readable text
    
    Args:
        html_text: Raw HTML content
        
    Returns:
        Clean text with HTML removed
    """
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text content
    text = soup.get_text()
    
    # Clean up whitespace and formatting while preserving line breaks
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line:  # Only keep non-empty lines
            lines.append(line)
    
    # Join lines with newlines to preserve structure
    text = '\n'.join(lines)
    
    # Remove excessive whitespace within lines but keep line breaks
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Remove common HTML artifacts and entities
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&apos;', "'", text)
    text = re.sub(r'&#160;', ' ', text)
    text = re.sub(r'&#8217;', "'", text)
    text = re.sub(r'&#8211;', '-', text)
    text = re.sub(r'&#8212;', '--', text)
    
    # Remove any remaining HTML-like patterns
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'/[^>]*>', '', text)
    text = re.sub(r'#160;', ' ', text)
    text = re.sub(r'br clear="none"', '', text)
    
    # Clean up any remaining artifacts while preserving line structure
    text = re.sub(r'[ \t]+', ' ', text)  # Only collapse spaces/tabs, not newlines
    text = text.strip()
    
    return text.strip()


def clean_financial_document(input_file, output_file=None):
    """
    Clean a financial document file
    
    Args:
        input_file: Path to input file
        output_file: Path to output file (optional, defaults to input_file_cleaned.txt)
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"File not found: {input_file}")
    
    # Read the file
    with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Clean the content
    cleaned_content = clean_html_content(content)
    
    # Determine output file
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_cleaned.txt"
    
    # Write cleaned content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_content)
    
    print(f"Cleaned HTML from {input_file}")
    print(f"Output saved to: {output_file}")
    print(f"Original size: {len(content)} chars")
    print(f"Cleaned size: {len(cleaned_content)} chars")
    
    return output_file


def clean_all_converted_files(directory="data/raw/earnings_reports"):
    """
    Clean all converted files in a directory
    
    Args:
        directory: Directory containing converted files
    """
    
    converted_files = [f for f in os.listdir(directory) if f.endswith('_converted.txt')]
    
    for filename in converted_files:
        input_path = os.path.join(directory, filename)
        try:
            clean_financial_document(input_path)
        except Exception as e:
            print(f"Error cleaning {filename}: {e}")
    
    print("HTML cleaning complete!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Clean specific file
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        clean_financial_document(input_file, output_file)
    else:
        # Clean all converted files
        clean_all_converted_files()
