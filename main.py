from transformers import BertTokenizer, BertForSequenceClassification
import torch
from pdf_parser import *
import os

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
    texts = [
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
    
    # Analyze a PDF file
    # pdf_text = extract_text_from_pdf("financial_text_files/NVDA-F2Q26-Quarterly-Presentation-FINAL.pdf")
    # sentiment = classify_sentiment(pdf_text)
    # print(f"PDF Sentiment: {sentiment}")
    


if __name__ == "__main__":
    main()