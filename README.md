**Authors:** Mikhail Saleev, Jordan Boskovich, Peter Ryan, Jackson Vonderhorst, Caden Chuang, Marco Basile

financial-nlp-engine/
├── data/
│ ├── raw/ # Raw earnings reports, news
│ ├── processed/ # Cleaned, structured data
│ └── output/ # Final JSON/CSV outputs
├── src/
│ ├── ingestion/ # Data collection modules
│ ├── parsing/ # Text extraction & parsing
│ ├── sentiment/ # Sentiment analysis
│ ├── extraction/ # Metric extraction (EPS, revenue, etc.)
│ ├── integration/ # Market data integration
│ └── utils/ # Helper functions
├── models/ # Trained models, weights
├── tests/ # Unit tests
└── main.py # Entry point
