import argparse
import os
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

def extract_ticker_from_title(title: str) -> str:
    """
    Extract ticker symbol from the title (e.g. 'BMY Earnings Call Transcript').
    Fallback: returns first capitalized word of length 2-5.
    """
    parts = title.split()
    for p in parts:
        if p.isupper() and 1 < len(p) <= 5:
            return p
    return "UNKNOWN"

def fetch_transcript(url: str) -> dict:
    """
    Downloads and parses a Motley Fool earnings transcript.
    Returns dict with title, date, url, and full text.
    """
    print(f"[INFO] Fetching URL: {url}")

    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch page: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title_elem = soup.find("h1")
    title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"

    # Extract ticker
    ticker = extract_ticker_from_title(title)
    print(f"[INFO] Detected ticker: {ticker}")

    # Extract main transcript text
    paragraphs = soup.find_all("p")
    transcript_text = "\n".join([p.get_text(strip=True) for p in paragraphs])

    return {
        "ticker": ticker,
        "title": title,
        "url": url,
        "date_fetched": datetime.utcnow().isoformat(),
        "content": transcript_text
    }

def save_transcript(data: dict):
    """
    Saves transcript JSON to data/raw/motley_fool/<TICKER>/
    """
    ticker = data["ticker"]
    output_dir = f"data/raw/motley_fool/{ticker}"
    os.makedirs(output_dir, exist_ok=True)

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"{ticker}_{date_str}.json"

    path = os.path.join(output_dir, filename)

    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[INFO] Saved transcript → {path}")

def main():
    parser = argparse.ArgumentParser(description="Fetch a Motley Fool earnings transcript.")
    parser.add_argument("--url", required=True, help="Full URL to Motley Fool transcript")
    args = parser.parse_args()

    data = fetch_transcript(args.url)
    save_transcript(data)

if __name__ == "__main__":
    main()


