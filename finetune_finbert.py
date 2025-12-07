"""
Fine-tune FinBERT on macroeconomic training data.
"""
import os
import sys
import json
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    BertTokenizer, 
    BertForSequenceClassification,
    TrainingArguments,
    Trainer
)
try:
    from transformers import EarlyStoppingCallback
except ImportError:
    EarlyStoppingCallback = None
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Label mapping for FinBERT (positive, negative, neutral)
LABEL_MAP = {'positive': 0, 'negative': 1, 'neutral': 2}
REVERSE_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}


class FinancialSentimentDataset(Dataset):
    """Dataset for financial sentiment classification."""
    
    def __init__(self, texts: list, labels: list, tokenizer, max_length: int = 512):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.texts)
    
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }


def load_training_data(data_path: str) -> tuple:
    """
    Load training data from JSON file.
    
    Expected format:
    [{"text": "...", "label": "positive"}, ...]
    
    Returns:
        Tuple of (texts, labels)
    """
    texts = []
    labels = []
    
    if data_path.endswith('.json'):
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                text = item.get('text', '')
                label = item.get('label', '').lower()
                
                if text and label in LABEL_MAP:
                    texts.append(text)
                    labels.append(LABEL_MAP[label])
    
    elif data_path.endswith('.csv'):
        df = pd.read_csv(data_path)
        for _, row in df.iterrows():
            text = str(row.get('text', ''))
            label = str(row.get('label', '')).lower()
            
            if text and label in LABEL_MAP:
                texts.append(text)
                labels.append(LABEL_MAP[label])
    
    else:
        raise ValueError(f"Unsupported file format: {data_path}")
    
    return texts, labels


def fine_tune(
    training_data_path: str,
    output_dir: str = 'models/finbert_finetuned',
    base_model: str = 'ProsusAI/finbert',
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    validation_split: float = 0.2,
    use_gpu: bool = True
):
    """
    Fine-tune FinBERT on custom training data.
    """
    # Detect device - prioritize MPS (Apple Silicon) > CUDA > CPU
    # Always try to use GPU if available
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        device = 'mps'
        print("🚀 Starting fine-tuning on device: MPS (Apple Silicon GPU)")
        print("   Using Metal Performance Shaders for acceleration")
    elif torch.cuda.is_available():
        device = 'cuda'
        print("🚀 Starting fine-tuning on device: CUDA (NVIDIA GPU)")
    else:
        device = 'cpu'
        print("⚠️  Starting fine-tuning on device: CPU (this will be slow)")
        print("   Consider using a machine with GPU support for faster training")
    
    # Load training data
    print("📂 Loading training data...")
    texts, labels = load_training_data(training_data_path)
    print(f"   Loaded {len(texts)} examples")
    
    if len(texts) == 0:
        raise ValueError("No valid training examples found!")
    
    # Show label distribution
    label_counts = {}
    for label in labels:
        label_name = REVERSE_LABEL_MAP[label]
        label_counts[label_name] = label_counts.get(label_name, 0) + 1
    
    print("   Label distribution:")
    for label, count in label_counts.items():
        print(f"     {label}: {count:,} examples")
    
    # Split into train/validation
    split_idx = int(len(texts) * (1 - validation_split))
    train_texts = texts[:split_idx]
    train_labels = labels[:split_idx]
    val_texts = texts[split_idx:]
    val_labels = labels[split_idx:]
    
    print(f"   Train: {len(train_texts)}, Validation: {len(val_texts)}")
    
    # Load tokenizer and model
    # Check if we should continue from existing fine-tuned model
    if os.path.exists(output_dir) and os.path.exists(os.path.join(output_dir, 'config.json')):
        print(f"📦 Loading existing fine-tuned model from {output_dir}...")
        print("   Continuing training from previous checkpoint...")
        tokenizer = BertTokenizer.from_pretrained(output_dir)
        model = BertForSequenceClassification.from_pretrained(output_dir)
    else:
        print(f"📦 Loading base model: {base_model}...")
        tokenizer = BertTokenizer.from_pretrained(base_model)
        model = BertForSequenceClassification.from_pretrained(base_model)
    
    # Move to device with proper handling for MPS
    if device == 'mps':
        # Clear MPS cache before loading
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        # Ensure model is on MPS
        model = model.to('mps')
        print("   ✅ Model loaded on MPS")
    else:
        model = model.to(device)
    
    # Create datasets
    train_dataset = FinancialSentimentDataset(train_texts, train_labels, tokenizer)
    val_dataset = FinancialSentimentDataset(val_texts, val_labels, tokenizer)
    
    # Training arguments
    os.makedirs(output_dir, exist_ok=True)
    
    # Adjust batch size for MPS (Apple Silicon) - smaller batches to avoid memory issues
    effective_batch_size = batch_size
    gradient_accumulation_steps = 1
    
    if device == 'mps':
        # MPS memory limits: 8GB unified memory can handle batch size 8-12 safely
        # Batch size 8 is the sweet spot for 8GB systems
        # For 16GB+ systems, can try 12-16
        effective_batch_size = min(batch_size, 12)  # Can try up to 12, but 8 is safer
        gradient_accumulation_steps = max(1, batch_size // effective_batch_size)
        print(f"   Using batch size {effective_batch_size} with {gradient_accumulation_steps} gradient accumulation steps")
        print(f"   Effective batch size: {effective_batch_size * gradient_accumulation_steps}")
    
    # Force device in training args for MPS
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=effective_batch_size,
        per_device_eval_batch_size=effective_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        weight_decay=0.01,
        logging_dir=f'{output_dir}/logs',
        logging_steps=50,
        eval_strategy='epoch',
        save_strategy='epoch',
        load_best_model_at_end=True,
        metric_for_best_model='accuracy',
        greater_is_better=True,
        save_total_limit=3,
        warmup_steps=100,
        dataloader_pin_memory=False,  # Disable pin_memory for MPS compatibility
        report_to='none',  # Disable wandb to reduce overhead
        fp16=False,  # Disable mixed precision for MPS stability
        # Explicitly set device
        no_cuda=(device != 'cuda'),  # Disable CUDA if not using it
    )
    
    # Override device in training args for MPS
    if device == 'mps':
        # The Trainer will use the device the model is on
        print("   ✅ Training will use MPS device")
    
    # Define compute_metrics function
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = predictions.argmax(axis=1)
        accuracy = (predictions == labels).mean()
        return {'accuracy': accuracy}
    
    # Create trainer
    callbacks = []
    if EarlyStoppingCallback:
        callbacks.append(EarlyStoppingCallback(early_stopping_patience=3))
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
        callbacks=callbacks if callbacks else None
    )
    
    # Ensure trainer uses correct device
    if device == 'mps':
        # Force MPS device
        trainer.model = trainer.model.to('mps')
        print("   ✅ Trainer configured for MPS")
    
    # Train
    print("🎓 Starting training...")
    trainer.train()
    
    # Save model
    print("💾 Saving fine-tuned model...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    # Evaluate
    print("📊 Evaluating model...")
    eval_results = trainer.evaluate()
    print(f"   Validation Accuracy: {eval_results['eval_accuracy']:.4f}")
    
    print(f"\n✅ Fine-tuning complete! Model saved to: {output_dir}")
    return model, tokenizer


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fine-tune FinBERT on macroeconomic data')
    parser.add_argument('--data', type=str, 
                       default='data/training_data/ground_truth/finbert_training_data.json',
                       help='Path to training data (JSON or CSV)')
    parser.add_argument('--output', type=str, default='models/finbert_finetuned',
                       help='Output directory for fine-tuned model')
    parser.add_argument('--epochs', type=int, default=3,
                       help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='Training batch size (default: 32)')
    parser.add_argument('--lr', type=float, default=2e-5,
                       help='Learning rate')
    parser.add_argument('--use-gpu', action='store_true', default=True,
                       help='Use GPU if available (default: True)')
    
    args = parser.parse_args()
    
    fine_tune(
        training_data_path=args.data,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        use_gpu=args.use_gpu
    )

