#!/usr/bin/env python3
"""
SEC EDGAR Scraper for extracting 10-Q statements by firm/CIK
"""

import requests
import json
import os
import time
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Tuple
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import zipfile
import io


class SECScraper:
    """Main class for scraping SEC EDGAR filings"""
    
    def __init__(self, rate_limit_delay: float = 0.5):
        """
        Initialize SEC scraper
        
        Args:
            rate_limit_delay: Delay between requests to respect rate limits
        """
        self.base_url = "https://www.sec.gov"
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Financial Analysis Tool (contact@example.com)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_company_tickers(self, cik: str) -> Dict[str, str]:
        """
        Get company ticker symbols and names from CIK
        
        Args:
            cik: Company CIK (10-digit string, zero-padded)
            
        Returns:
            Dictionary with ticker and company name
        """
        cik_padded = cik.zfill(10)
        url = f"{self.base_url}/cgi-bin/browse-edgar?CIK={cik_padded}&owner=exclude&action=getcompany"
        
        try:
            # Add delay before request
            time.sleep(self.rate_limit_delay)
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 403:
                print(f"SEC blocked request for CIK {cik}. This is common - trying alternative approach...")
                # Try with a different approach or return basic info
                return {'name': f'Company_{cik}', 'ticker': 'UNKNOWN'}
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract company name and ticker
            company_info = {}
            
            # Look for company name in the page title or headers
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text()
                # Extract company name from title (usually in format "Company Name (TICKER)")
                match = re.search(r'([^(]+)\s*\(([^)]+)\)', title_text)
                if match:
                    company_info['name'] = match.group(1).strip()
                    company_info['ticker'] = match.group(2).strip()
                else:
                    company_info['name'] = title_text.strip()
            
            # Look for ticker in the page content
            if 'ticker' not in company_info:
                ticker_pattern = r'CIK.*?(\d{10}).*?([A-Z]{1,5})'
                ticker_match = re.search(ticker_pattern, response.text)
                if ticker_match:
                    company_info['ticker'] = ticker_match.group(2)
            
            return company_info
            
        except Exception as e:
            print(f"Error getting company info for CIK {cik}: {e}")
            return {'name': f'Company_{cik}', 'ticker': 'UNKNOWN'}
    
    def get_filings_api(self, cik: str, form_type: str = '10-Q', max_filings: int = 5) -> List[Dict]:
        """
        Get filings using SEC's JSON API (more reliable than web scraping)
        
        Args:
            cik: Company CIK
            form_type: Type of form to search for
            max_filings: Maximum number of filings to return
            
        Returns:
            List of filing dictionaries
        """
        cik_padded = cik.zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        
        try:
            time.sleep(self.rate_limit_delay)
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 403:
                print(f"SEC API blocked request for CIK {cik}. This is common.")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            filings = []
            recent_filings = data.get('filings', {}).get('recent', {})
            
            if not recent_filings:
                return filings
            
            # Get form types, filing dates, and accession numbers
            form_types = recent_filings.get('form', [])
            filing_dates = recent_filings.get('filingDate', [])
            accession_numbers = recent_filings.get('accessionNumber', [])
            primary_documents = recent_filings.get('primaryDocument', [])
            
            # Filter for the requested form type
            for i, (form, date, accession, primary_doc) in enumerate(zip(form_types, filing_dates, accession_numbers, primary_documents)):
                if form == form_type and len(filings) < max_filings:
                    filing = {
                        'filing_type': form,
                        'filing_date': date,
                        'accession_number': accession,
                        'filing_url': f"https://www.sec.gov/Archives/edgar/data/{cik_padded}/{accession.replace('-', '')}/{primary_doc}",
                        'primary_document': primary_doc
                    }
                    filings.append(filing)
            
            return filings
            
        except Exception as e:
            print(f"Error getting filings via API for CIK {cik}: {e}")
            return []

    def get_filings(self, cik: str, form_type: str = '10-Q', 
                   start_date: Optional[str] = None, 
                   end_date: Optional[str] = None,
                   max_filings: int = 5) -> List[Dict]:
        """
        Get list of filings for a company
        
        Args:
            cik: Company CIK
            form_type: Type of form to search for (10-Q, 10-K, etc.)
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            max_filings: Maximum number of filings to return
            
        Returns:
            List of filing dictionaries
        """
        cik_padded = cik.zfill(10)
        
        # Build URL with parameters
        params = {
            'CIK': cik_padded,
            'type': form_type,
            'owner': 'exclude',
            'action': 'getcompany'
        }
        
        if start_date:
            params['dateb'] = start_date
        if end_date:
            params['datea'] = end_date
        
        url = f"{self.base_url}/cgi-bin/browse-edgar"
        
        try:
            # Add delay before request
            time.sleep(self.rate_limit_delay)
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 403:
                print(f"SEC blocked request for CIK {cik}. This is common - trying alternative approach...")
                return []
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            filings = []
            
            # Find the table with filings
            table = soup.find('table', {'class': 'tableFile'})
            if not table:
                print(f"No filings found for CIK {cik} and form type {form_type}")
                return filings
            
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for i, row in enumerate(rows):
                if i >= max_filings:
                    break
                    
                cells = row.find_all('td')
                if len(cells) >= 4:
                    filing = {
                        'filing_type': cells[0].get_text().strip(),
                        'filing_date': cells[3].get_text().strip(),
                        'filing_url': None,
                        'accession_number': None
                    }
                    
                    # Get the filing URL
                    link = cells[1].find('a')
                    if link:
                        filing['filing_url'] = urljoin(self.base_url, link.get('href'))
                        # Extract accession number from URL
                        accession_match = re.search(r'AccessionNumber=([^&]+)', filing['filing_url'])
                        if accession_match:
                            filing['accession_number'] = accession_match.group(1)
                    
                    filings.append(filing)
            
            return filings
            
        except Exception as e:
            print(f"Error getting filings for CIK {cik}: {e}")
            return []
    
    def get_filing_documents(self, filing_url: str) -> List[Dict]:
        """
        Get list of documents within a filing
        
        Args:
            filing_url: URL to the filing page
            
        Returns:
            List of document dictionaries
        """
        try:
            response = self.session.get(filing_url)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            documents = []
            
            # Find the table with documents
            table = soup.find('table', {'class': 'tableFile'})
            if not table:
                return documents
            
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    doc_name = cells[2].get_text().strip()
                    doc_type = cells[1].get_text().strip()
                    
                    # Get the document URL
                    link = cells[2].find('a')
                    if link:
                        doc_url = urljoin(self.base_url, link.get('href'))
                        documents.append({
                            'name': doc_name,
                            'type': doc_type,
                            'url': doc_url
                        })
            
            return documents
            
        except Exception as e:
            print(f"Error getting documents from {filing_url}: {e}")
            return []
    
    def download_document(self, doc_url: str, output_path: str) -> bool:
        """
        Download a document from SEC EDGAR
        
        Args:
            doc_url: URL to the document
            output_path: Local path to save the document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.session.get(doc_url)
            response.raise_for_status()
            time.sleep(self.rate_limit_delay)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save the document
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return True
            
        except Exception as e:
            print(f"Error downloading document from {doc_url}: {e}")
            return False
    
    def extract_text_from_html(self, html_content: str) -> str:
        """
        Extract clean text from HTML content, filtering out XBRL data
        
        Args:
            html_content: HTML content as string
            
        Returns:
            Clean text content with XBRL data removed
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Filter out XBRL data - look for the pattern that indicates start of actual content
        # XBRL data typically ends and real content begins with "UNITED STATES" or "FORM"
        xbrl_end_markers = [
            "UNITED STATES",
            "SECURITIES AND EXCHANGE COMMISSION", 
            "FORM 10-Q",
            "FORM 10-K",
            "FORM 8-K",
            "QUARTERLY REPORT",
            "ANNUAL REPORT",
            "CURRENT REPORT"
        ]
        
        # Find the first occurrence of any of these markers
        for marker in xbrl_end_markers:
            marker_pos = text.find(marker)
            if marker_pos != -1:
                # Keep everything from the marker onwards
                text = text[marker_pos:]
                break
        
        # Clean up whitespace and add logical line breaks
        # First, add line breaks at common sentence/paragraph boundaries
        text = text.replace('. ', '.\n')
        text = text.replace('? ', '?\n')
        text = text.replace('! ', '!\n')
        text = text.replace(') ', ')\n')
        text = text.replace('] ', ']\n')
        text = text.replace('} ', '}\n')
        
        # Add line breaks before common section headers
        section_headers = [
            'Item ', 'FORM ', 'Pursuant to', 'Check the appropriate', 
            'Securities registered', 'Indicate by check', 'UNITED STATES',
            'Date of Report', 'Apple Inc.', 'California', 'One Apple Park',
            'Not applicable', 'Emerging growth company', 'SIGNATURE',
            'ExhibitNumber', 'Exhibit Description'
        ]
        
        for header in section_headers:
            text = text.replace(header, f'\n{header}')
        
        # Clean up the text
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line:  # Only keep non-empty lines
                lines.append(line)
        
        text = '\n'.join(lines)
        
        return text
    
    def scrape_10q_filings(self, cik: str, company_name: str, 
                          max_filings: int = 5, 
                          output_dir: str = 'data/raw/earnings_reports',
                          ticker: str = None) -> List[str]:
        """
        Main method to scrape 10-Q filings for a company
        
        Args:
            cik: Company CIK
            company_name: Company name
            max_filings: Maximum number of filings to download
            output_dir: Output directory for saved files
            
        Returns:
            List of saved file paths
        """
        # Get 10-Q filings using API first, fallback to web scraping
        filings = self.get_filings_api(cik, form_type='10-Q', max_filings=max_filings)
        
        if not filings:
            filings = self.get_filings(cik, form_type='10-Q', max_filings=max_filings)
        
        if not filings:
            print("No 10-Q filings found")
            return []
        
        saved_files = []
        
        for i, filing in enumerate(filings, 1):
            if not filing.get('filing_url'):
                continue
            
            # Use provided ticker or get from company info
            if not ticker:
                company_info = self.get_company_tickers(cik)
                ticker = company_info.get('ticker', 'UNKNOWN')
            
            # Create simple filename: TICKER_10Q_NUMBER.txt
            temp_html_filename = f"{ticker}_10Q_{i}.html"
            temp_html_path = os.path.join(output_dir, temp_html_filename)
            
            # Download the document to temporary file
            if self.download_document(filing['filing_url'], temp_html_path):
                # Extract and save as text
                try:
                    with open(temp_html_path, 'r', encoding='utf-8', errors='ignore') as f:
                        html_content = f.read()
                    
                    text_content = self.extract_text_from_html(html_content)
                    
                    # Save as text file
                    text_filename = temp_html_filename.replace('.html', '.txt')
                    text_filepath = os.path.join(output_dir, text_filename)
                    
                    with open(text_filepath, 'w', encoding='utf-8') as f:
                        f.write(text_content)
                    
                    print(f"✓ {text_filename}")
                    saved_files.append(text_filepath)
                    
                    # Remove the temporary HTML file
                    os.remove(temp_html_path)
                    
                except Exception as e:
                    print(f"✗ Error extracting text: {e}")
                    # Clean up temp file even if extraction fails
                    if os.path.exists(temp_html_path):
                        os.remove(temp_html_path)
        
        return saved_files


def get_company_name(cik: str) -> str:
    """
    Get company name from CIK using SEC company tickers API
    
    Args:
        cik: Company CIK
        
    Returns:
        Company name
    """
    try:
        # Use the more reliable SEC company tickers API
        import requests
        import time
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Financial Analysis Tool (msaleev@nd.edu)',
            'Accept': 'application/json',
        })
        
        time.sleep(0.5)  # Rate limiting
        url = "https://www.sec.gov/files/company_tickers.json"
        response = session.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            cik_padded = cik.zfill(10)
            
            # Search for the CIK in the API data
            for entry in data.values():
                cik_raw = entry.get('cik_str', '')
                if isinstance(cik_raw, (int, str)) and str(cik_raw).zfill(10) == cik_padded:
                    return entry.get('title', f'Company_{cik}')
        
        # Fallback to original method if API fails
        scraper = SECScraper()
        company_info = scraper.get_company_tickers(cik)
        return company_info.get('name', f'Company_{cik}')
        
    except Exception as e:
        print(f"Error getting company name for CIK {cik}: {e}")
        # Fallback to original method
        scraper = SECScraper()
        company_info = scraper.get_company_tickers(cik)
        return company_info.get('name', f'Company_{cik}')


def execute_scraping(cik: str, company_name: str, form_types: List[str] = ['10-Q'], 
                    max_filings: int = 5, output_dir: str = 'data/raw/earnings_reports',
                    ticker: str = None) -> List[str]:
    """
    Execute scraping for specified parameters
    
    Args:
        cik: Company CIK
        company_name: Company name
        form_types: List of form types to scrape
        max_filings: Maximum number of filings per form type
        output_dir: Output directory
        
    Returns:
        List of saved file paths
    """
    scraper = SECScraper()
    all_saved_files = []
    
    for form_type in form_types:
        if form_type == '10-Q':
            saved_files = scraper.scrape_10q_filings(cik, company_name, max_filings, output_dir, ticker)
        else:
            # For other form types, use API method first, fallback to web scraping
            filings = scraper.get_filings_api(cik, form_type, max_filings=max_filings)
            
            if not filings:
                filings = scraper.get_filings(cik, form_type, max_filings=max_filings)
            
            if not filings:
                print(f"No {form_type} filings found")
                continue
                
            saved_files = []
            
            for i, filing in enumerate(filings, 1):
                if not filing.get('filing_url'):
                    continue
                
                # Use provided ticker or get from company info
                if not ticker:
                    company_info = scraper.get_company_tickers(cik)
                    ticker = company_info.get('ticker', 'UNKNOWN')
                
                # Create simple filename: TICKER_FORMTYPE_NUMBER.txt
                temp_html_filename = f"{ticker}_{form_type}_{i}.html"
                temp_html_path = os.path.join(output_dir, temp_html_filename)
                
                # Download the document to temporary file
                if scraper.download_document(filing['filing_url'], temp_html_path):
                    # Extract and save as text
                    try:
                        with open(temp_html_path, 'r', encoding='utf-8', errors='ignore') as f:
                            html_content = f.read()
                        
                        text_content = scraper.extract_text_from_html(html_content)
                        
                        # Save as text file
                        text_filename = temp_html_filename.replace('.html', '.txt')
                        text_filepath = os.path.join(output_dir, text_filename)
                        
                        with open(text_filepath, 'w', encoding='utf-8') as f:
                            f.write(text_content)
                        
                        print(f"✓ {text_filename}")
                        saved_files.append(text_filepath)
                        
                        # Remove the temporary HTML file
                        os.remove(temp_html_path)
                        
                    except Exception as e:
                        print(f"✗ Error extracting text: {e}")
                        # Clean up temp file even if extraction fails
                        if os.path.exists(temp_html_path):
                            os.remove(temp_html_path)
        
        all_saved_files.extend(saved_files)
    
    return all_saved_files


if __name__ == "__main__":
    # Example usage
    scraper = SECScraper()
    
    # Example: Scrape NVIDIA 10-Q filings
    cik = "0001045810"  # NVIDIA CIK
    company_name = "NVIDIA Corporation"
    
    saved_files = scraper.scrape_10q_filings(cik, company_name, max_filings=3)
    print(f"\nDownloaded {len(saved_files)} files")
