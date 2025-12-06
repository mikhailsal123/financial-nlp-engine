# Macroeconomic Training Data

This directory contains training data generated from FRED (Federal Reserve Economic Data) macroeconomic growth indicators.

## Structure

```
data/training_data/
├── data/                          # Raw data files
│   ├── A191RL1Q225SBEA_data.csv  # Real GDP Growth Rate data
│   ├── GDPC1_data.csv            # Real GDP data
│   ├── PAYEMS_data.csv           # Employment data
│   └── ...
├── ground_truth/                  # Labeled training data
│   ├── A191RL1Q225SBEA_ground_truth.csv
│   ├── all_indicators_ground_truth.csv  # Combined CSV
│   └── finbert_training_data.json       # JSON format for FinBERT
└── metadata.json                   # Dataset metadata
```

## Generating Data

Run the generation script:

```bash
python generate_macro_training_data.py
```

Or with custom date range:

```bash
python generate_macro_training_data.py \
    --start-date 2020-01-01 \
    --end-date 2024-12-31 \
    --output-dir data/training_data
```

## Indicators Included

1. **Real GDP Growth Rate** (A191RL1Q225SBEA) - Quarterly
2. **Real Gross Domestic Product** (GDPC1) - Quarterly
3. **Total Nonfarm Payrolls** (PAYEMS) - Monthly
4. **Unemployment Rate** (UNRATE) - Monthly
5. **Industrial Production Index** (INDPRO) - Monthly
6. **Retail Sales** (RSAFS) - Monthly
7. **Consumer Sentiment Index** (UMCSENT) - Monthly
8. **Manufacturing Employment** (MANEMP) - Monthly
9. **Housing Starts** (HOUST) - Monthly
10. **Corporate Profits After Tax** (A053RC1Q027SBEA) - Quarterly

## Data Format

### Ground Truth CSV Format

| date | text | sentiment | value | change | series_id | indicator_name |
|------|------|-----------|-------|--------|-----------|----------------|
| 2024-01-01 | Real GDP Growth Rate increased by 2.5 Percent... | positive | 2.5 | 0.3 | A191RL1Q225SBEA | Real GDP Growth Rate |

### Training JSON Format

```json
[
  {
    "text": "Real GDP Growth Rate increased by 2.5 Percent to 2.5 Percent in 2024-01-01.",
    "label": "positive",
    "date": "2024-01-01",
    "indicator": "Real GDP Growth Rate",
    "series_id": "A191RL1Q225SBEA",
    "value": 2.5,
    "change": 0.3
  }
]
```

## Sentiment Labeling Rules

Labels are assigned based on indicator-specific thresholds:

- **Positive**: Strong growth/improvement (e.g., GDP growth > 2%, job growth > 100k)
- **Negative**: Decline/recession (e.g., GDP decline, job losses)
- **Neutral**: Moderate growth or no change

Each indicator has custom thresholds appropriate for its scale and economic significance.

## Usage

### For FinBERT Training

Use the JSON file directly:

```bash
python src/sentiment/finetune_finbert.py \
    --data data/training_data/ground_truth/finbert_training_data.json
```

### For Analysis

Load the combined CSV:

```python
import pandas as pd

df = pd.read_csv('data/training_data/ground_truth/all_indicators_ground_truth.csv')
print(df['sentiment'].value_counts())
```

## Requirements

- FRED_API_KEY environment variable must be set
- See `requirements.txt` for Python dependencies

