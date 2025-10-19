"""
Simple SEC EDGAR scraper with automatic XBRL conversion
"""

import os
import json
import re
import sys
from datetime import datetime
from typing import List, Dict

# Add src/parsing to path for XBRL converter
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'parsing'))
from xbrl_converter import convert_xbrl_to_text


def get_company_name(cik: str) -> str:
    """Get company name from CIK using SEC API"""
    import requests
    
    try:
        clean_cik = cik.lstrip('0')
        padded_cik = clean_cik.zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"
        
        headers = {
            'User-Agent': 'Financial NLP Engine (msaleev@nd.edu)',
            'Accept': 'application/json',
            'Host': 'data.sec.gov'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        return data.get('name', 'Unknown Company')
        
    except Exception as e:
        print(f"Error looking up company name: {e}")
        return "Unknown Company"


def scrape_company_filings(company_name: str, 
                          cik: str,
                          form_types: List[str] = ['10-Q', '10-K'],
                          max_filings: int = 5,
                          output_dir: str = "data/processed/earnings_reports") -> List[str]:
    """
    Scrape company filings from SEC EDGAR using direct API calls
    
    Args:
        company_name: Company name
        cik: Company CIK
        form_types: List of form types to scrape
        max_filings: Maximum number of filings to download per type
        output_dir: Output directory
        
    Returns:
        List of saved filenames
    """
    import requests
    import re
    from datetime import datetime
    
    print(f"Scraping {company_name} (CIK: {cik}) filings...")
    
    os.makedirs(output_dir, exist_ok=True)
    saved_files = []
    
    try:
        # Get company filings from SEC API
        clean_cik = cik.lstrip('0')
        padded_cik = clean_cik.zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"
        
        headers = {
            'User-Agent': 'Financial NLP Engine (msaleev@nd.edu)',
            'Accept': 'application/json',
            'Host': 'data.sec.gov'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Process each form type
        for form_type in form_types:
            print(f"Getting {form_type} filings...")
            
            # Find filings of this type
            form_filings = []
            for i, form in enumerate(data['filings']['recent']['form']):
                if form == form_type:
                    filing_date = data['filings']['recent']['filingDate'][i]
                    accession = data['filings']['recent']['accessionNumber'][i]
                    form_filings.append({
                        'date': filing_date,
                        'accession': accession,
                        'index': i
                    })
            
            if len(form_filings) == 0:
                print(f"No {form_type} filings found")
                continue
            
            print(f"Found {len(form_filings)} {form_type} filings")
            
            # Process the most recent filings
            for i, filing in enumerate(form_filings[:max_filings]):
                try:
                    print(f"Processing {form_type} filing {i+1}/{min(len(form_filings), max_filings)}... ({filing['date']})")
                    
                    # Construct document URL - need to format accession number properly
                    accession = filing['accession']
                    # Format: 0000320193-25-000073 -> 000032019325000073 (for directory)
                    accession_clean = accession.replace('-', '')
                    # The URL format is: https://www.sec.gov/Archives/edgar/data/CIK/accession_clean/accession.txt
                    # Use the original CIK with leading zeros, not the cleaned version
                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{accession}.txt"
                    
                    # Download the document with appropriate headers
                    doc_headers = {
                        'User-Agent': 'Financial NLP Engine (msaleev@nd.edu)',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Host': 'www.sec.gov'
                    }
                    doc_response = requests.get(doc_url, headers=doc_headers)
                    if doc_response.status_code == 200:
                        text_content = doc_response.text
                        
                        # Create temporary file for XBRL conversion
                        temp_filename = f"temp_{cik}_{form_type}_{filing['date']}.txt"
                        temp_filepath = os.path.join(output_dir, temp_filename)
                        
                        # Save raw content temporarily
                        with open(temp_filepath, 'w', encoding='utf-8') as f:
                            f.write(text_content)
                        
                        # Convert XBRL to plain text
                        converted_filename = f"{cik}_{company_name.replace(' ', '_')}_{form_type}_{filing['date']}_converted.txt"
                        converted_filepath = os.path.join(output_dir, converted_filename)
                        
                        try:
                            # Use XBRL converter to extract financial data
                            convert_xbrl_to_text(temp_filepath, converted_filepath)
                            
                            # Check if conversion produced meaningful content
                            if os.path.exists(converted_filepath):
                                with open(converted_filepath, 'r', encoding='utf-8') as f:
                                    converted_content = f.read()
                                
                                if len(converted_content.strip()) > 1000:  # Meaningful content
                                    # Clean HTML from the converted content
                                    from html_cleaner import clean_html_content
                                    cleaned_content = clean_html_content(converted_content)
                                    
                                    # Save the cleaned content
                                    with open(converted_filepath, 'w', encoding='utf-8') as f:
                                        f.write(cleaned_content)
                                    
                                    saved_files.append(converted_filename)
                                    print(f"Converted, cleaned, and saved: {converted_filename} ({len(cleaned_content)} chars)")
                                    
                                    # Remove temporary file
                                    os.remove(temp_filepath)
                                else:
                                    print(f"Skipped filing {i+1} - insufficient content after conversion")
                                    # Clean up both files
                                    if os.path.exists(converted_filepath):
                                        os.remove(converted_filepath)
                                    os.remove(temp_filepath)
                            else:
                                print(f"XBRL conversion failed for filing {i+1}")
                                os.remove(temp_filepath)
                                
                        except Exception as conv_error:
                            print(f"Error converting XBRL for filing {i+1}: {conv_error}")
                            # Clean up temporary file
                            if os.path.exists(temp_filepath):
                                os.remove(temp_filepath)
                            if os.path.exists(converted_filepath):
                                os.remove(converted_filepath)
                    else:
                        print(f"Failed to download filing {i+1}: HTTP {doc_response.status_code}")
                    
                except Exception as e:
                    print(f"Error processing filing {i+1}: {e}")
                    continue
        
        print(f"Successfully saved {len(saved_files)} filings for {company_name}")
        return saved_files
        
    except Exception as e:
        print(f"Error scraping {company_name}: {e}")
        return []


def execute_scraping(cik: str, company_name: str, **kwargs):
    """
    Execute the scraping process
    
    Args:
        cik: Company CIK
        company_name: Company name
        **kwargs: Additional arguments for scrape_company_filings
    """
    return scrape_company_filings(company_name, cik, **kwargs)