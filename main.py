from transformers import BertTokenizer, BertForSequenceClassification
import torch
import os
import sys
from text_parser import *

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

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
    
    # Analyze downloaded 10-Q files
    print("Analyzing downloaded 10-Q files:")
    earnings_dir = "data/raw/earnings_reports"
    if os.path.exists(earnings_dir):
        for filename in os.listdir(earnings_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(earnings_dir, filename)
                print(f"\nAnalyzing {filename}:")
                analyze_text_file(filepath)

if __name__ == "__main__":
    main()