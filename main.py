from transformers import BertTokenizer, BertForSequenceClassification
import torch
from pdf_parser import extract_text_from_pdf
import os

# Load model ONCE when script starts (outside any function)
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
        
     # Analyze entire text as one document
    sentiment = classify_sentiment(text)
        
    print(f"Document sentiment: {sentiment}")
    print(f"Text preview: {text[:200]}...")


def main():
    # Example 1: Analyze individual sentences
    print("=== INDIVIDUAL SENTENCE ANALYSIS ===")
    texts = [
        "The company reported strong quarterly earnings growth.",
        "Terrible losses this quarter.",
        "Revenue remained flat compared to last year."
    ]
    
    for text in texts:
        sentiment = classify_sentiment(text)
        print(f"Text: {text}")
        print(f"Sentiment: {sentiment}\n")
    
    # Example 2: Analyze text file
    print("=== TEXT FILE ANALYSIS ===")
    analyze_text_file("text.txt")
    
    # Example 3: Analyze PDF (uncomment to use)
    # print("=== PDF ANALYSIS ===")
    # pdf_text = extract_text_from_pdf("report_files/NVDA-F2Q26-Quarterly-Presentation-FINAL.pdf")
    # sentiment = classify_sentiment(pdf_text)
    # print(f"PDF Sentiment: {sentiment}")
    


if __name__ == "__main__":
    main()