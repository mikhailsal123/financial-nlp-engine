"""
Test the fine-tuned FinBERT model on the training data to verify classification accuracy.
"""
import os
import sys
import json
import pandas as pd
import torch
from transformers import BertTokenizer, BertForSequenceClassification

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def load_finetuned_model(model_path='models/finbert_finetuned'):
    """Load the fine-tuned model."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at {model_path}. Training may not be complete.")
    
    print(f"📦 Loading fine-tuned model from: {model_path}")
    tokenizer = BertTokenizer.from_pretrained(model_path)
    model = BertForSequenceClassification.from_pretrained(model_path)
    
    # Set device
    if torch.backends.mps.is_available():
        device = 'mps'
    elif torch.cuda.is_available():
        device = 'cuda'
    else:
        device = 'cpu'
    
    model.to(device)
    model.eval()
    print(f"✅ Model loaded on device: {device}")
    return model, tokenizer, device

def classify_sentiment(text, model, tokenizer, device):
    """Classify sentiment of a text."""
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model(**inputs)
        predictions = outputs.logits.argmax(dim=1)
    
    sentiment_labels = list(model.config.id2label.values())
    return sentiment_labels[predictions.item()]

def test_on_training_data(data_path='data/training_data/ground_truth/finbert_training_data.json'):
    """Test the fine-tuned model on training data."""
    print("="*80)
    print("TESTING FINE-TUNED MODEL ON TRAINING DATA")
    print("="*80)
    print()
    
    # Load model
    model, tokenizer, device = load_finetuned_model()
    print()
    
    # Load training data
    print(f"📂 Loading test data from: {data_path}")
    with open(data_path, 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    print(f"   Loaded {len(test_data)} examples")
    print()
    
    # Test on all examples
    print("🔍 Testing model predictions...")
    correct = 0
    total = 0
    confusion_matrix = {
        'positive': {'positive': 0, 'negative': 0, 'neutral': 0},
        'negative': {'positive': 0, 'negative': 0, 'neutral': 0},
        'neutral': {'positive': 0, 'negative': 0, 'neutral': 0}
    }
    
    results = []
    
    for i, example in enumerate(test_data):
        text = example['text']
        true_label = example['label'].lower()
        
        # Predict
        predicted_label = classify_sentiment(text, model, tokenizer, device)
        
        # Check if correct
        is_correct = (predicted_label.lower() == true_label)
        if is_correct:
            correct += 1
        total += 1
        
        # Update confusion matrix
        confusion_matrix[true_label][predicted_label.lower()] += 1
        
        results.append({
            'text': text[:100] + '...' if len(text) > 100 else text,
            'true_label': true_label,
            'predicted_label': predicted_label.lower(),
            'correct': is_correct
        })
        
        # Print progress
        if (i + 1) % 50 == 0:
            print(f"   Processed {i + 1}/{len(test_data)} examples...")
    
    # Calculate accuracy
    accuracy = (correct / total) * 100
    
    print()
    print("="*80)
    print("RESULTS")
    print("="*80)
    print(f"Total examples: {total:,}")
    print(f"Correct predictions: {correct:,}")
    print(f"Accuracy: {accuracy:.2f}%")
    print()
    
    # Confusion matrix
    print("Confusion Matrix:")
    print("-"*80)
    print(f"{'True\\Predicted':<15} {'Positive':<12} {'Negative':<12} {'Neutral':<12}")
    print("-"*80)
    for true_label in ['positive', 'negative', 'neutral']:
        row = f"{true_label.capitalize():<15}"
        for pred_label in ['positive', 'negative', 'neutral']:
            count = confusion_matrix[true_label][pred_label]
            row += f"{count:<12}"
        print(row)
    print()
    
    # Per-class accuracy
    print("Per-Class Accuracy:")
    print("-"*80)
    for label in ['positive', 'negative', 'neutral']:
        total_class = sum(confusion_matrix[label].values())
        correct_class = confusion_matrix[label][label]
        if total_class > 0:
            class_acc = (correct_class / total_class) * 100
            print(f"{label.capitalize():<15}: {correct_class}/{total_class} = {class_acc:.2f}%")
    print()
    
    # Show some examples
    print("Sample Predictions (first 10):")
    print("-"*80)
    for i, result in enumerate(results[:10], 1):
        status = "✅" if result['correct'] else "❌"
        print(f"{i}. {status} True: {result['true_label']:8s} | Predicted: {result['predicted_label']:8s}")
        print(f"   Text: {result['text']}")
        print()
    
    # Show incorrect predictions
    incorrect = [r for r in results if not r['correct']]
    if incorrect:
        print(f"\nIncorrect Predictions ({len(incorrect)} total):")
        print("-"*80)
        for i, result in enumerate(incorrect[:10], 1):
            print(f"{i}. True: {result['true_label']:8s} | Predicted: {result['predicted_label']:8s}")
            print(f"   Text: {result['text']}")
            print()
    
    return accuracy, results

if __name__ == "__main__":
    try:
        accuracy, results = test_on_training_data()
        print("="*80)
        print(f"✅ Testing complete! Model accuracy: {accuracy:.2f}%")
        print("="*80)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nThe fine-tuned model is not available yet.")
        print("Please wait for training to complete, or check if training was successful.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

