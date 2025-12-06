import os
import requests
from pathlib import Path

FRED_BASE_URL = "https://api.stlouisfed.org/fred"


def _get_api_key() -> str:
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY environment variable not set.")
    return key


def get_series_info(series_id: str) -> dict:
    api_key = _get_api_key()
    url = f"{FRED_BASE_URL}/series"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    if "seriess" in data and data["seriess"]:
        return data["seriess"][0]
    return {}


def _compute_label(change: float | None) -> str:
    """Return good/bad/neutral label based strictly on change value."""  # >>> ADDED
    if change is None:
        return "neutral"

    if change > 0:
        return "good"
    elif change < 0:
        return "bad"
    else:
        return "neutral"


def download_series(
    series_id: str,
    start_date: str | None,
    end_date: str | None,
    frequency: str | None,
    output_dir: str,
    fmt: str = "csv",
    max_rows: int | None = None,
) -> str:

    api_key = _get_api_key()
    url = f"{FRED_BASE_URL}/series/observations"

    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }

    if start_date:
        params["observation_start"] = start_date
    if end_date:
        params["observation_end"] = end_date
    if frequency:
        params["frequency"] = frequency
    if max_rows:
        params["limit"] = max_rows

    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    observations = data.get("observations", [])

    # =======================================================
    # >>> ADDED: compute change + label for each observation
    # =======================================================
    for i, obs in enumerate(observations):

        # parse value
        try:
            value = float(obs.get("value", ""))
        except:
            obs["change"] = None  # >>> ADDED
            obs["label"] = "neutral"  # >>> ADDED
            continue

        # first row baseline
        if i == 0:
            obs["change"] = 0  # >>> ADDED
            obs["label"] = "neutral"  # >>> ADDED
        else:
            try:
                prev_value = float(observations[i-1].get("value", ""))
                change = value - prev_value    # >>> ADDED
            except:
                change = None

            obs["change"] = change               # >>> ADDED
            obs["label"] = _compute_label(change)  # >>> ADDED

    # -------------------------------------------------------
    # Save directory
    # -------------------------------------------------------
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------
    # JSON EXPORT (now includes change + label)
    # -------------------------------------------------------
    if fmt == "json":
        # >>> ADDED: embed enriched observations back into JSON
        data["observations"] = observations  # >>> ADDED

        out_path = outdir / f"{series_id}.json"
        out_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
        return str(out_path)

    # -------------------------------------------------------
    # CSV EXPORT (now date,value,change,label)
    # -------------------------------------------------------
    lines = ["date,value,change,label"]  # >>> UPDATED HEADER

    for obs in observations:
        date = obs.get("date", "")
        value = obs.get("value", "")
        change = obs.get("change", "")
        label = obs.get("label", "")  # >>> ADDED

        lines.append(f"{date},{value},{change},{label}")  # >>> UPDATED

    csv_path = outdir / f"{series_id}.csv"
    csv_path.write_text("\n".join(lines), encoding="utf-8")

    return str(csv_path)