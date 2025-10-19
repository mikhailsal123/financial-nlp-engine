from transformers import BertTokenizer, BertForSequenceClassification
import torch
import os
from text_parser import *

# Load model when script starts
print("Loading FinBERT model...")
tokenizer = BertTokenizer.from_pretrained('ProsusAI/finbert')
model = BertForSequenceClassification.from_pretrained('ProsusAI/finbert')

def classify_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    with torch.no_grad():
        outputs = model(**inputs)
        predictions = outputs.logits.argmax(dim=1)
    
    sentiment_labels = list(model.config.id2label.values())
    return sentiment_labels[predictions.item()]

def analyze_text_file(file_path):
    """Analyze sentiment of entire text file as one document"""
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
        
     # Analyze text as one document
    sentiment = classify_sentiment(text)
        
    print(f"Document sentiment: {sentiment}")
    print(f"Text preview: {text[:200]}...")


def main():
    
    # Analyze individual sentences
    '''texts = [
        "The company reported strong quarterly earnings growth.",
        "Terrible losses this quarter.",
        "Revenue remained flat compared to last year."
    ]
    
    for text in texts:
        sentiment = classify_sentiment(text)
        print(f"Text: {text}")
        print(f"Sentiment: {sentiment}\n")
    
    # Analyze a text file
    analyze_text_file("text.txt")
    
    # Analyze a PDF file (if it exists)
    pdf_path = "data/raw/NVDA-F2Q26-Quarterly-Presentation-FINAL.pdf"
    if os.path.exists(pdf_path):
        pdf_text = extract_text_from_pdf(pdf_path)
        sentiment = classify_sentiment(pdf_text)
        print(f"PDF Sentiment: {sentiment}")
    else:
        print("PDF file not found, skipping PDF analysis")'''
    
    # Analyze financial reports
    reports_dir = "data/processed/earnings_reports"
    
    # Get all converted files
    converted_files = []
    for filename in os.listdir(reports_dir):
        converted_files.append(os.path.join(reports_dir, filename))
    
    print(f"Analyzing {len(converted_files)} financial reports...")
    
    for file_path in sorted(converted_files):
        print(f"\nAnalyzing: {os.path.basename(file_path)}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Analyze overall document sentiment
        sentiment = classify_sentiment(content)
        print(f"Document Sentiment: {sentiment}")
            
        # Show preview of content

if __name__ == "__main__":
    main()