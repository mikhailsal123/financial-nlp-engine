"""
Simple PDF + Motley Fool transcript parser.

Usage (from repo root):

    python text_parser.py --ticker BMY

This will:
  - Look for the latest Motley Fool JSON in:
        data/raw/motley_fool/(TICKER)/*.json
  - Clean the transcript text
  - Save a .txt file into:
        data/processed/motley_fool/
"""

import os
import re
import json
import argparse
from datetime import datetime

# ---------------------------------------------------------------------------
# Optional: PDF helper (not used for Motley JSON right now, but kept for group)
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file."""
    import PyPDF2

    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

# ---------------------------------------------------------------------------
# Cleaning logic for Motley Fool JSON transcripts
# ---------------------------------------------------------------------------

def clean_motley_text(raw: str) -> str:
    """
    Clean Motley Fool transcript text loaded from JSON.
    Adjust this as needed depending on the JSON structure.
    """
    if not isinstance(raw, str):
        return ""

    # Replace escaped newlines with real newlines
    raw = raw.replace("\\n", "\n")

    # Remove weird unicode escapes like \u00a0 (non-breaking space)
    raw = raw.encode("utf-8", "ignore").decode("utf-8")

    # Collapse crazy whitespace
    text = re.sub(r"[ \t]+", " ", raw)
    text = re.sub(r"\n\s+\n", "\n\n", text)

    return text.strip()

# ---------------------------------------------------------------------------
# JSON loading for Motley Fool data
# ---------------------------------------------------------------------------

def load_latest_motley_json(ticker: str, raw_root: str = "data/raw/motley_fool"):
    """
    Load the latest Motley Fool JSON file for a ticker.

    Expected directory layout (for ticker BMY):

        data/raw/motley_fool/(BMY)/(BMY)_2025-12-06.json

    Returns:
        (date_string, transcript_text)
    """
    ticker = ticker.upper()

    # The fetch script creates a subfolder like "(BMY)"
    raw_dir = os.path.join(raw_root, f"({ticker})")

    if not os.path.isdir(raw_dir):
        raise FileNotFoundError(f"No directory for ticker {ticker} found at {raw_dir}")

    # Collect all JSON files in that folder
    candidates = [f for f in os.listdir(raw_dir) if f.lower().endswith(".json")]
    if not candidates:
        raise FileNotFoundError(
            f"No Motley Fool JSON files found for ticker {ticker} in {raw_dir}"
        )

    # Sort alphabetically – filenames include the date, so last = latest
    candidates.sort()
    latest = candidates[-1]
    json_path = os.path.join(raw_dir, latest)

    with open(json_path, "r") as f:
        data = json.load(f)

    # Try a few likely keys for the transcript body
    text = (
        data.get("transcript")
        or data.get("content")
        or data.get("text")
        or ""
    )

    if not text:
        raise KeyError(
            f"Could not find transcript text in JSON file {json_path}. "
            "Tried keys: 'transcript', 'content', 'text'."
        )

    # Try to pull the date from the filename: e.g. "(BMY)_2025-12-06.json"
    base = os.path.splitext(latest)[0]
    # base might be "(BMY)_2025-12-06"
    if "_" in base:
        date_part = base.split("_")[-1]
    else:
        date_part = datetime.utcnow().strftime("%Y-%m-%d")

    return date_part, text

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Parse Motley Fool transcript JSON.")
    parser.add_argument(
        "--ticker",
        required=True,
        help="Ticker symbol (e.g., BMY, NVDA)",
    )
    args = parser.parse_args()
    ticker = args.ticker.upper()

    # 1. Load latest JSON
    date_str, raw_text = load_latest_motley_json(ticker)

    # 2. Clean text
    cleaned = clean_motley_text(raw_text)

    # 3. Save to processed dir
    processed_dir = os.path.join("data", "processed", "motley_fool")
    os.makedirs(processed_dir, exist_ok=True)

    out_name = f"{ticker}_{date_str}.txt"
    out_path = os.path.join(processed_dir, out_name)

    with open(out_path, "w") as f:
        f.write(cleaned)

    print(f"[INFO] Loaded latest JSON for {ticker} (date {date_str})")
    print(f"[INFO] Saved cleaned transcript -> {out_path}")

if __name__ == "__main__":
    main()

