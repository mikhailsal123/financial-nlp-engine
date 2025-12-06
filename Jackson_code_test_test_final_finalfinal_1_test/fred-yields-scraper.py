import os
import pandas as pd
from fredapi import Fred
from dotenv import load_dotenv

# Load keys from .env file (if available)
load_dotenv()

# FRED API Key
FRED_API_KEY = os.getenv("FRED_API_KEY") or "3ac4454be8eadcec434106ae2fcf4921"

fred = Fred(api_key=FRED_API_KEY)

# Real GDP Growth Rate (Quarterly, Percent Change from Preceding Period)
series_id = "A191RL1Q225SBEA"

print("Downloading data...")
data = fred.get_series(series_id)

# Clean the data
df = pd.DataFrame(data, columns=["value"])
df.index.name = "date"
df.reset_index(inplace=True)

# Save
df.to_csv("gdp_growth_rate.csv", index=False)

print("Saved gdp_growth_rate.csv")

