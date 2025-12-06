# FinBERT Web Interface

A locally hosted web application for testing and analyzing FinBERT sentiment classification.

## Features

- **Test Model**: Test sentiment classification on custom text
- **Batch Testing**: Analyze multiple texts at once
- **Performance Metrics**: View model performance statistics
- **Analysis Results**: Browse and view results from processed files
- **Data Downloads**: Download training data and analysis results

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure the fine-tuned model exists:
```bash
# Model should be at: ../models/finbert_finetuned/
```

3. Run the application:
```bash
python app.py
```

4. Open in browser:
```
http://localhost:5000
```

## Usage

### Test Model Tab
- Enter text in the textarea
- Click "Analyze Sentiment" to get classification
- Use "Batch Test" for multiple texts (one per line)

### Performance Tab
- View model accuracy and metrics
- See training data statistics

### Results Tab
- Browse all analysis results
- Click on a result to see detailed section-by-section analysis

### Data Downloads Tab
- Download training data (CSV)
- Download all analysis results (JSON)

## Notes

- **No training on website**: Training must be done separately using `finetune_finbert.py`
- Model is loaded at startup
- All data is read-only (no modifications allowed)

