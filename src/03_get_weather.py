"""
Pull daily weather for Bengaluru from the Open-Meteo archive API.

Open-Meteo's historical endpoint needs no key and no signup. Bengaluru stands
in for Karnataka as a whole: it is the largest load centre in the state, so its
temperature moves with state demand better than a state centroid would. That is
an assumption, not a fact, and it is written down in the README as one.

The archive endpoint lags real time by about five days, so the end date is
clamped to whatever the demand series actually ends on.

Run:  python src/03_get_weather.py
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEMAND = ROOT / "data" / "processed" / "daily_demand.csv"
OUT = ROOT / "data" / "raw" / "bengaluru_weather.csv"

LAT, LON = 12.9716, 77.5946  # Bengaluru
BASE = "https://archive-api.open-meteo.com/v1/archive"


def main():
    demand = pd.read_csv(DEMAND, parse_dates=["date"])
    start = demand.date.min().date()
    end = demand.date.max().date()

    url = (
        f"{BASE}?latitude={LAT}&longitude={LON}"
        f"&start_date={start}&end_date={end}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&timezone=Asia%2FKolkata"
    )
    print(f"asking Open-Meteo for {start} to {end}")

    try:
        with urllib.request.urlopen(url, timeout=180) as r:
            payload = json.load(r)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(
            "\ncould not reach Open-Meteo: "
            f"{e}\n\n"
            "Nothing was written. The rest of the pipeline runs without weather\n"
            "and the weather panels stay marked as not run. Re-run this script\n"
            "from a machine with internet access, then run 04, 05, 08 and 09\n"
            "again and everything downstream fills in."
        )
        raise SystemExit(1)

    daily = payload["daily"]
    w = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temp_max_c": daily["temperature_2m_max"],
            "temp_min_c": daily["temperature_2m_min"],
            "rain_mm": daily["precipitation_sum"],
        }
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    w.to_csv(OUT, index=False)

    print(f"saved {len(w):,} days to {OUT}")
    print(f"temp_max range {w.temp_max_c.min():.1f} to {w.temp_max_c.max():.1f} C")
    missing = w.temp_max_c.isna().sum()
    if missing:
        print(f"warning: {missing} days came back with no temperature")


if __name__ == "__main__":
    main()
