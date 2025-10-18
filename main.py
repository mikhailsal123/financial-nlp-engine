from transformers import BertTokenizer, BertForSequenceClassification
import torch


def main():
    # Download and load the tokenizer
    tokenizer = BertTokenizer.from_pretrained('ProsusAI/finbert')
    # Download and load the model
    model = BertForSequenceClassification.from_pretrained('ProsusAI/finbert')

    # Example financial text
    text = "The company reported strong quarterly earnings growth."
    
    # Tokenize the text
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    
    # Get model predictions
    with torch.no_grad():
        outputs = model(**inputs)
        predictions = outputs.logits.argmax(dim=1)
        logits = outputs.logits
    
    # Debug: Let's see the raw output
    print(f"Raw logits: {logits}")
    print(f"Predicted class: {predictions.item()}")
    print(f"Model config labels: {model.config.label2id}")
    
    # Use the model's actual label mapping
    sentiment_labels = list(model.config.id2label.values())
    sentiment = sentiment_labels[predictions.item()]
    
    print(f"Text: {text}")
    print(f"Sentiment: {sentiment}")
    


if __name__ == "__main__":
    main()