"""
Generate training data from FRED macroeconomic growth indicators.
Fetches GDP growth and other growth indicators, creates ground truth labels,
and organizes data for training.
"""
import os
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.fred_client import download_series, get_series_info
from src.fred_lookup import search_series

# Load API key with fallback
from dotenv import load_dotenv
load_dotenv()
if not os.getenv("FRED_API_KEY"):
    os.environ["FRED_API_KEY"] = "3ac4454be8eadcec434106ae2fcf4921"

# Macroeconomic growth indicators to fetch
MACRO_INDICATORS = {
    # GDP and Economic Growth
    'A191RL1Q225SBEA': {
        'name': 'Real GDP Growth Rate',
        'description': 'Real Gross Domestic Product, Percent Change from Preceding Period',
        'unit': 'Percent',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 2.5,  # Strong growth (>2.5% is healthy)
            'negative': lambda x: x < 0,     # Recession/decline
            'neutral': lambda x: 0 <= x <= 2.5  # Moderate/slow growth
        }
    },
    'GDPC1': {
        'name': 'Real Gross Domestic Product',
        'description': 'Real GDP in Billions of Chained 2017 Dollars',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 0,    # Growth
            'negative': lambda x: x < 0,    # Decline
            'neutral': lambda x: x == 0     # No change
        }
    },
    # Employment Growth
    'PAYEMS': {
        'name': 'Total Nonfarm Payrolls',
        'description': 'Total Nonfarm Employment, Change from Previous Period',
        'unit': 'Thousands',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 90,  # Strong job growth (>90k/month is healthy)
            'negative': lambda x: x < 0,    # Job losses
            'neutral': lambda x: 0 <= x <= 90  # Moderate growth
        }
    },
    'UNRATE': {
        'name': 'Unemployment Rate',
        'description': 'Unemployment Rate, Change from Previous Period',
        'unit': 'Percent',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x < -0.2,  # Significant decrease (>0.2% drop is good)
            'negative': lambda x: x > 0.2,   # Significant increase (>0.2% rise is bad)
            'neutral': lambda x: -0.2 <= x <= 0.2  # Stable (small changes)
        }
    },
    # Industrial Production Growth
    'INDPRO': {
        'name': 'Industrial Production Index',
        'description': 'Industrial Production Index, Percent Change from Previous Period',
        'unit': 'Percent',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 0.8,  # Strong production growth (>0.8% monthly)
            'negative': lambda x: x < 0,    # Production decline
            'neutral': lambda x: 0 <= x <= 0.8  # Moderate growth
        }
    },
    # Retail Sales Growth
    'RSAFS': {
        'name': 'Retail Sales',
        'description': 'Retail and Food Services Sales, Change from Previous Period',
        'unit': 'Millions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 2000,  # Strong sales growth (>$2B monthly)
            'negative': lambda x: x < 0,    # Sales decline
            'neutral': lambda x: 0 <= x <= 2000  # Moderate growth
        }
    },
    # Consumer Confidence
    'UMCSENT': {
        'name': 'Consumer Sentiment Index',
        'description': 'University of Michigan Consumer Sentiment Index, Change',
        'unit': 'Index',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 3,    # Significant improvement (>3 points)
            'negative': lambda x: x < -3,   # Significant decline (<-3 points)
            'neutral': lambda x: -3 <= x <= 3  # Stable (normal fluctuation)
        }
    },
    # Manufacturing Growth
    'MANEMP': {
        'name': 'Manufacturing Employment',
        'description': 'Manufacturing Employment, Change from Previous Period',
        'unit': 'Thousands',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 20,    # Strong manufacturing job growth (>20k)
            'negative': lambda x: x < 0,    # Manufacturing job losses
            'neutral': lambda x: 0 <= x <= 20  # Moderate growth/stable
        }
    },
    # Housing Starts Growth
    'HOUST': {
        'name': 'Housing Starts',
        'description': 'New Privately Owned Housing Units Started, Change',
        'unit': 'Thousands',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 10,    # Strong housing growth (>10k units)
            'negative': lambda x: x < 0,    # Housing decline
            'neutral': lambda x: 0 <= x <= 10  # Moderate growth
        }
    },
    # Corporate Profits Growth
    'A053RC1Q027SBEA': {
        'name': 'Corporate Profits After Tax',
        'description': 'Corporate Profits After Tax, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 50,    # Strong profit growth (>$50B quarterly)
            'negative': lambda x: x < 0,     # Profit decline
            'neutral': lambda x: 0 <= x <= 50  # Moderate growth
        }
    },
    # Interest Rates
    'FEDFUNDS': {
        'name': 'Federal Funds Rate',
        'description': 'Effective Federal Funds Rate, Change from Previous Period',
        'unit': 'Percent',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x < -0.25,  # Rate cut (stimulative, generally positive)
            'negative': lambda x: x > 0.25,   # Rate hike (restrictive, can be negative)
            'neutral': lambda x: -0.25 <= x <= 0.25  # Stable rates
        }
    },
    'DGS10': {
        'name': '10-Year Treasury Rate',
        'description': '10-Year Treasury Constant Maturity Rate, Change',
        'unit': 'Percent',
        'frequency': 'Daily',
        'sentiment_mapping': {
            'positive': lambda x: x < -0.1,  # Falling yields (positive for bonds, can indicate economic concerns)
            'negative': lambda x: x > 0.1,   # Rising yields (can indicate inflation concerns)
            'neutral': lambda x: -0.1 <= x <= 0.1  # Stable
        }
    },
    # Inflation Indicators
    'CPIAUCSL': {
        'name': 'Consumer Price Index',
        'description': 'Consumer Price Index for All Urban Consumers, Percent Change',
        'unit': 'Percent',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: 1.5 <= x <= 2.5,  # Healthy inflation (target range)
            'negative': lambda x: x > 3.0 or x < 0,  # High inflation or deflation (both bad)
            'neutral': lambda x: (0 <= x < 1.5) or (2.5 < x <= 3.0)  # Low or slightly high
        }
    },
    'PPIACO': {
        'name': 'Producer Price Index',
        'description': 'Producer Price Index for All Commodities, Percent Change',
        'unit': 'Percent',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: 0 <= x <= 2.0,  # Moderate producer price growth
            'negative': lambda x: x > 3.0 or x < -0.5,  # High inflation or deflation
            'neutral': lambda x: (2.0 < x <= 3.0) or (-0.5 <= x < 0)  # Borderline
        }
    },
    # Stock Market Indicators
    'SP500': {
        'name': 'S&P 500 Index',
        'description': 'S&P 500 Index, Percent Change from Previous Period',
        'unit': 'Percent',
        'frequency': 'Daily',
        'sentiment_mapping': {
            'positive': lambda x: x > 1.0,   # Strong gains (>1% daily)
            'negative': lambda x: x < -1.0,  # Significant losses (<-1% daily)
            'neutral': lambda x: -1.0 <= x <= 1.0  # Normal volatility
        }
    },
    'VIXCLS': {
        'name': 'VIX Volatility Index',
        'description': 'CBOE Volatility Index, Change',
        'unit': 'Index',
        'frequency': 'Daily',
        'sentiment_mapping': {
            'positive': lambda x: x < -2.0,  # Falling volatility (calm markets, positive)
            'negative': lambda x: x > 2.0,   # Rising volatility (fear, negative)
            'neutral': lambda x: -2.0 <= x <= 2.0  # Stable volatility
        }
    },
    # Trade Balance
    'BOPGSTB': {
        'name': 'Trade Balance',
        'description': 'Trade Balance: Goods and Services, Change from Previous Period',
        'unit': 'Millions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 5000,  # Improving trade balance (less deficit or more surplus)
            'negative': lambda x: x < -5000,  # Worsening trade balance (larger deficit)
            'neutral': lambda x: -5000 <= x <= 5000  # Stable
        }
    },
    # Personal Income and Spending
    'PI': {
        'name': 'Personal Income',
        'description': 'Personal Income, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 50,    # Strong income growth (>$50B monthly)
            'negative': lambda x: x < 0,     # Income decline
            'neutral': lambda x: 0 <= x <= 50  # Moderate growth
        }
    },
    'PCE': {
        'name': 'Personal Consumption Expenditures',
        'description': 'Personal Consumption Expenditures, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 30,    # Strong consumer spending (>$30B monthly)
            'negative': lambda x: x < 0,     # Spending decline
            'neutral': lambda x: 0 <= x <= 30  # Moderate growth
        }
    },
    # Business Inventories
    'BUSINV': {
        'name': 'Total Business Inventories',
        'description': 'Total Business Inventories, Change from Previous Period',
        'unit': 'Millions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: 0 < x <= 10000,  # Moderate inventory growth (healthy demand)
            'negative': lambda x: x < 0 or x > 20000,  # Declining or excessive inventory buildup
            'neutral': lambda x: (x == 0) or (10000 < x <= 20000)  # Stable or high buildup
        }
    },
    # Credit and Debt
    'TOTALSL': {
        'name': 'Total Consumer Credit',
        'description': 'Total Consumer Credit Outstanding, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: 5 <= x <= 20,  # Moderate credit growth (healthy borrowing)
            'negative': lambda x: x < 0 or x > 30,  # Credit contraction or excessive growth
            'neutral': lambda x: (0 <= x < 5) or (20 < x <= 30)  # Low or high growth
        }
    },
    # Additional Economic Indicators
    'DEXUSEU': {
        'name': 'U.S. / Euro Foreign Exchange Rate',
        'description': 'U.S. Dollars to Euro Spot Exchange Rate, Change',
        'unit': 'Dollars',
        'frequency': 'Daily',
        'sentiment_mapping': {
            'positive': lambda x: -0.05 <= x <= 0.05,  # Stable exchange rate
            'negative': lambda x: abs(x) > 0.1,  # High volatility (uncertainty)
            'neutral': lambda x: 0.05 < abs(x) <= 0.1  # Moderate movement
        }
    },
    'DEXCHUS': {
        'name': 'China / U.S. Foreign Exchange Rate',
        'description': 'Chinese Yuan to U.S. Dollar Spot Exchange Rate, Change',
        'unit': 'Yuan',
        'frequency': 'Daily',
        'sentiment_mapping': {
            'positive': lambda x: -0.05 <= x <= 0.05,  # Stable exchange rate
            'negative': lambda x: abs(x) > 0.1,  # High volatility
            'neutral': lambda x: 0.05 < abs(x) <= 0.1  # Moderate movement
        }
    },
    'DEXJPUS': {
        'name': 'Japan / U.S. Foreign Exchange Rate',
        'description': 'Japanese Yen to U.S. Dollar Spot Exchange Rate, Change',
        'unit': 'Yen',
        'frequency': 'Daily',
        'sentiment_mapping': {
            'positive': lambda x: -2.0 <= x <= 2.0,  # Stable exchange rate
            'negative': lambda x: abs(x) > 5.0,  # High volatility
            'neutral': lambda x: 2.0 < abs(x) <= 5.0  # Moderate movement
        }
    },
    'GPDI': {
        'name': 'Gross Private Domestic Investment',
        'description': 'Gross Private Domestic Investment, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 50,  # Strong investment growth (>$50B quarterly)
            'negative': lambda x: x < 0,  # Investment decline
            'neutral': lambda x: 0 <= x <= 50  # Moderate growth
        }
    },
    'EXPGSC1': {
        'name': 'Government Consumption Expenditures',
        'description': 'Government Consumption Expenditures and Gross Investment, Change',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: 10 <= x <= 100,  # Moderate government spending growth
            'negative': lambda x: x < 0 or x > 150,  # Decline or excessive growth
            'neutral': lambda x: (0 <= x < 10) or (100 < x <= 150)  # Low or high growth
        }
    },
    'A191RO1Q156NBEA': {
        'name': 'Real Gross Domestic Product per Capita',
        'description': 'Real GDP per Capita, Percent Change from Preceding Period',
        'unit': 'Percent',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 1.5,  # Strong per capita growth (>1.5%)
            'negative': lambda x: x < 0,  # Decline
            'neutral': lambda x: 0 <= x <= 1.5  # Moderate growth
        }
    },
    'PCEDG': {
        'name': 'Personal Consumption Expenditures: Durable Goods',
        'description': 'PCE: Durable Goods, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 5,  # Strong durable goods spending (>$5B monthly)
            'negative': lambda x: x < 0,  # Decline
            'neutral': lambda x: 0 <= x <= 5  # Moderate growth
        }
    },
    'PCEND': {
        'name': 'Personal Consumption Expenditures: Nondurable Goods',
        'description': 'PCE: Nondurable Goods, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 3,  # Strong nondurable goods spending (>$3B monthly)
            'negative': lambda x: x < 0,  # Decline
            'neutral': lambda x: 0 <= x <= 3  # Moderate growth
        }
    },
    'PCES': {
        'name': 'Personal Consumption Expenditures: Services',
        'description': 'PCE: Services, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 20,  # Strong services spending (>$20B monthly)
            'negative': lambda x: x < 0,  # Decline
            'neutral': lambda x: 0 <= x <= 20  # Moderate growth
        }
    },
    'DEXUSUK': {
        'name': 'U.S. / U.K. Foreign Exchange Rate',
        'description': 'U.S. Dollars to U.K. Pound Spot Exchange Rate, Change',
        'unit': 'Dollars',
        'frequency': 'Daily',
        'sentiment_mapping': {
            'positive': lambda x: -0.05 <= x <= 0.05,  # Stable exchange rate
            'negative': lambda x: abs(x) > 0.1,  # High volatility
            'neutral': lambda x: 0.05 < abs(x) <= 0.1  # Moderate movement
        }
    },
    # Additional Economic Indicators for More Training Data
    'W875RX1': {
        'name': 'Real Personal Income Excluding Current Transfer Receipts',
        'description': 'Real Personal Income Excluding Current Transfer Receipts, Change',
        'unit': 'Billions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 30,  # Strong income growth (>$30B monthly)
            'negative': lambda x: x < 0,  # Income decline
            'neutral': lambda x: 0 <= x <= 30  # Moderate growth
        }
    },
    'DSPIC96': {
        'name': 'Real Disposable Personal Income',
        'description': 'Real Disposable Personal Income, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Monthly',
        'sentiment_mapping': {
            'positive': lambda x: x > 25,  # Strong disposable income growth (>$25B monthly)
            'negative': lambda x: x < 0,  # Decline
            'neutral': lambda x: 0 <= x <= 25  # Moderate growth
        }
    },
    'A955RC1Q027SBEA': {
        'name': 'Gross Domestic Product: Imports',
        'description': 'GDP: Imports of Goods and Services, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: 0 <= x <= 50,  # Moderate import growth (healthy trade)
            'negative': lambda x: x < -20 or x > 100,  # Sharp decline or excessive growth
            'neutral': lambda x: (-20 <= x < 0) or (50 < x <= 100)  # Borderline
        }
    },
    'A957RC1Q027SBEA': {
        'name': 'Gross Domestic Product: Exports',
        'description': 'GDP: Exports of Goods and Services, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 30,  # Strong export growth (>$30B quarterly)
            'negative': lambda x: x < 0,  # Export decline
            'neutral': lambda x: 0 <= x <= 30  # Moderate growth
        }
    },
    'A794RC0Q052SBEA': {
        'name': 'Real Gross Private Domestic Investment',
        'description': 'Real Gross Private Domestic Investment, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 40,  # Strong investment growth (>$40B quarterly)
            'negative': lambda x: x < 0,  # Investment decline
            'neutral': lambda x: 0 <= x <= 40  # Moderate growth
        }
    },
    'A955RX1Q020SBEA': {
        'name': 'Real Gross Domestic Product: Imports of Goods',
        'description': 'Real GDP: Imports of Goods, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: 0 <= x <= 40,  # Moderate import growth
            'negative': lambda x: x < -15 or x > 80,  # Sharp decline or excessive growth
            'neutral': lambda x: (-15 <= x < 0) or (40 < x <= 80)  # Borderline
        }
    },
    'A957RX1Q020SBEA': {
        'name': 'Real Gross Domestic Product: Exports of Goods',
        'description': 'Real GDP: Exports of Goods, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 25,  # Strong export growth (>$25B quarterly)
            'negative': lambda x: x < 0,  # Export decline
            'neutral': lambda x: 0 <= x <= 25  # Moderate growth
        }
    },
    'A006RC1Q027SBEA': {
        'name': 'Gross Domestic Product: Final Sales to Domestic Purchasers',
        'description': 'GDP: Final Sales to Domestic Purchasers, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 100,  # Strong domestic demand (>$100B quarterly)
            'negative': lambda x: x < 0,  # Decline
            'neutral': lambda x: 0 <= x <= 100  # Moderate growth
        }
    },
    'A191RL1Q225SBEA': {
        'name': 'Real Gross Domestic Product per Capita',
        'description': 'Real GDP per Capita, Percent Change from Preceding Period',
        'unit': 'Percent',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 1.5,  # Strong per capita growth (>1.5%)
            'negative': lambda x: x < 0,  # Decline
            'neutral': lambda x: 0 <= x <= 1.5  # Moderate growth
        }
    },
    'A939RC0Q052SBEA': {
        'name': 'Real Gross Domestic Product: Government Consumption Expenditures',
        'description': 'Real GDP: Government Consumption Expenditures, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: 5 <= x <= 50,  # Moderate government spending growth
            'negative': lambda x: x < 0 or x > 80,  # Decline or excessive growth
            'neutral': lambda x: (0 <= x < 5) or (50 < x <= 80)  # Low or high growth
        }
    },
    'A955RX1Q027SBEA': {
        'name': 'Real Gross Domestic Product: Imports of Services',
        'description': 'Real GDP: Imports of Services, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: 0 <= x <= 15,  # Moderate service import growth
            'negative': lambda x: x < -5 or x > 30,  # Sharp decline or excessive growth
            'neutral': lambda x: (-5 <= x < 0) or (15 < x <= 30)  # Borderline
        }
    },
    'A957RX1Q027SBEA': {
        'name': 'Real Gross Domestic Product: Exports of Services',
        'description': 'Real GDP: Exports of Services, Change from Previous Period',
        'unit': 'Billions',
        'frequency': 'Quarterly',
        'sentiment_mapping': {
            'positive': lambda x: x > 10,  # Strong service export growth (>$10B quarterly)
            'negative': lambda x: x < 0,  # Export decline
            'neutral': lambda x: 0 <= x <= 10  # Moderate growth
        }
    }
}


def compute_sentiment_label(value: float, change: float, indicator_config: dict) -> str:
    """
    Compute sentiment label based on change value and indicator-specific rules.
    
    Args:
        value: Current value
        change: Change from previous period
        indicator_config: Configuration dict with sentiment_mapping
    
    Returns:
        Sentiment label: 'positive', 'negative', or 'neutral'
    """
    if change is None:
        return 'neutral'
    
    mapping = indicator_config.get('sentiment_mapping', {})
    
    # Check each sentiment condition
    for sentiment, condition in mapping.items():
        if condition(change):
            return sentiment
    
    # Default to neutral if no condition matches
    return 'neutral'


def fetch_macro_data(
    start_date: str = None,
    end_date: str = None,
    output_dir: str = 'data/training_data'
):
    """
    Fetch macroeconomic growth data from FRED and organize for training.
    
    Args:
        start_date: Start date (YYYY-MM-DD), defaults to 5 years ago
        end_date: End date (YYYY-MM-DD), defaults to today
        output_dir: Output directory for training data
    """
    # Set default dates - extend to 20 years for maximum data
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=20*365)).strftime('%Y-%m-%d')
    
    # Create output directories
    base_dir = Path(output_dir)
    data_dir = base_dir / 'data'
    ground_truth_dir = base_dir / 'ground_truth'
    
    data_dir.mkdir(parents=True, exist_ok=True)
    ground_truth_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*80)
    print("FETCHING MACROECONOMIC GROWTH DATA FROM FRED")
    print("="*80)
    print(f"Date range: {start_date} to {end_date}")
    print(f"Output directory: {output_dir}")
    print()
    
    all_data = []
    all_ground_truth = []
    metadata = []
    
    for series_id, config in MACRO_INDICATORS.items():
        print(f"📊 Fetching {config['name']} ({series_id})...")
        
        try:
            # Get series info
            series_info = get_series_info(series_id)
            if not series_info:
                print(f"   ⚠️  Series not found, skipping...")
                continue
            
            # Download series data
            # Determine frequency from config
            freq_map = {'Quarterly': 'q', 'Monthly': 'm', 'Weekly': 'w', 'Daily': 'd'}
            frequency = freq_map.get(config.get('frequency', 'Monthly'), None)
            
            csv_path = download_series(
                series_id=series_id,
                start_date=start_date,
                end_date=end_date,
                frequency=frequency,
                output_dir=str(data_dir),
                fmt='csv'
            )
            
            # Read the CSV
            df = pd.read_csv(csv_path)
            
            # Compute sentiment labels based on change
            df['sentiment'] = df.apply(
                lambda row: compute_sentiment_label(
                    row['value'] if pd.notna(row['value']) else None,
                    row['change'] if pd.notna(row['change']) else None,
                    config
                ),
                axis=1
            )
            
            # Create text descriptions for training
            df['text'] = df.apply(
                lambda row: create_text_description(
                    config['name'],
                    row['date'],
                    row['value'] if pd.notna(row['value']) else None,
                    row['change'] if pd.notna(row['change']) else None,
                    config['unit']
                ),
                axis=1
            )
            
            # Prepare ground truth data
            ground_truth = df[['date', 'text', 'sentiment', 'value', 'change']].copy()
            ground_truth['series_id'] = series_id
            ground_truth['indicator_name'] = config['name']
            ground_truth = ground_truth[ground_truth['text'].notna()]  # Remove rows with missing data
            
            # Save individual files
            ground_truth_file = ground_truth_dir / f"{series_id}_ground_truth.csv"
            ground_truth.to_csv(ground_truth_file, index=False)
            
            # Save raw data with labels
            data_file = data_dir / f"{series_id}_data.csv"
            df.to_csv(data_file, index=False)
            
            # Collect for combined files
            all_ground_truth.append(ground_truth)
            all_data.append(df)
            
            # Store metadata
            metadata.append({
                'series_id': series_id,
                'name': config['name'],
                'description': config['description'],
                'unit': config['unit'],
                'frequency': config['frequency'],
                'observations': len(ground_truth),
                'data_file': str(data_file.relative_to(base_dir)),
                'ground_truth_file': str(ground_truth_file.relative_to(base_dir))
            })
            
            print(f"   ✅ Fetched {len(ground_truth)} observations")
            
        except Exception as e:
            print(f"   ❌ Error fetching {series_id}: {e}")
            continue
    
    # Combine all data
    if all_ground_truth:
        print()
        print("📝 Creating combined files...")
        
        combined_ground_truth = pd.concat(all_ground_truth, ignore_index=True)
        combined_ground_truth_file = ground_truth_dir / 'all_indicators_ground_truth.csv'
        combined_ground_truth.to_csv(combined_ground_truth_file, index=False)
        print(f"   ✅ Combined ground truth: {len(combined_ground_truth)} examples")
        
        # Create JSON format for training
        training_json = []
        for _, row in combined_ground_truth.iterrows():
            training_json.append({
                'text': row['text'],
                'label': row['sentiment'],
                'date': row['date'],
                'indicator': row['indicator_name'],
                'series_id': row['series_id'],
                'value': float(row['value']) if pd.notna(row['value']) else None,
                'change': float(row['change']) if pd.notna(row['change']) else None
            })
        
        json_file = ground_truth_dir / 'finbert_training_data.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(training_json, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Training JSON: {len(training_json)} examples")
        
        # Save metadata
        metadata_file = base_dir / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                'generated_date': datetime.now().isoformat(),
                'date_range': {'start': start_date, 'end': end_date},
                'indicators': metadata,
                'total_examples': len(training_json),
                'label_distribution': combined_ground_truth['sentiment'].value_counts().to_dict()
            }, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Metadata saved")
    
    print()
    print("="*80)
    print("✅ DATA GENERATION COMPLETE")
    print("="*80)
    print(f"📁 Data directory: {data_dir}")
    print(f"📁 Ground truth directory: {ground_truth_dir}")
    print()
    if all_ground_truth:
        print("Label distribution:")
        dist = combined_ground_truth['sentiment'].value_counts()
        for label, count in dist.items():
            print(f"  {label:10s}: {count:,} examples")


def create_text_description(
    indicator_name: str,
    date: str,
    value: float,
    change: float,
    unit: str
) -> str:
    """
    Create a natural language description of the economic indicator.
    
    Args:
        indicator_name: Name of the indicator
        date: Date of observation
        value: Current value
        change: Change from previous period
        unit: Unit of measurement
    
    Returns:
        Natural language description
    """
    if pd.isna(value) or pd.isna(change):
        return None
    
    # Format change direction
    if change > 0:
        direction = "increased"
        change_str = f"{abs(change):.2f}"
    elif change < 0:
        direction = "decreased"
        change_str = f"{abs(change):.2f}"
    else:
        direction = "remained unchanged"
        change_str = ""
    
    # Format value
    if abs(value) >= 1000000:
        value_str = f"${value/1000000:.2f} billion"
    elif abs(value) >= 1000:
        value_str = f"${value/1000:.2f} million"
    else:
        value_str = f"{value:.2f}"
    
    # Create description
    if change != 0:
        description = (
            f"{indicator_name} {direction} by {change_str} {unit} "
            f"to {value_str} {unit} in {date}."
        )
    else:
        description = (
            f"{indicator_name} {direction} at {value_str} {unit} in {date}."
        )
    
    return description


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate macroeconomic training data from FRED')
    parser.add_argument('--start-date', type=str, default=None,
                       help='Start date (YYYY-MM-DD), defaults to 5 years ago')
    parser.add_argument('--end-date', type=str, default=None,
                       help='End date (YYYY-MM-DD), defaults to today')
    parser.add_argument('--output-dir', type=str, default='data/training_data',
                       help='Output directory for training data')
    
    args = parser.parse_args()
    
    fetch_macro_data(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output_dir
    )

