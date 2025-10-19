"""
Simple PDF parser
"""

import os
import re
import PyPDF2


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF files"""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text