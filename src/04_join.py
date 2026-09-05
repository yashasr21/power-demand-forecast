"""
Build the one table everything downstream reads: demand, calendar, weather.

Lags are taken on the calendar, not on the row above. The series has 154 missing
days, so a row-based shift would quietly compare a Tuesday to the Friday before
it and call that "yesterday". Where the real previous day is missing the lag is
left empty and the model drops that row.

Weather is optional. If data/raw/bengaluru_weather.csv is not there the columns
come out empty and the weather model is skipped, with that fact recorded in
data/processed/weather_status.txt so the dashboard can say so honestly.

Output
    data/processed/model_input.csv

Run:  python src/04_join.py
"""

from pathlib import Path

import holidays
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
DEMAND = PROC / "daily_demand.csv"
WEATHER = ROOT / "data" / "raw" / "bengaluru_weather.csv"
OUT = PROC / "model_input.csv"


def main():
    d = pd.read_csv(DEMAND, parse_dates=["date"]).sort_values("date")

    # Reindex onto every calendar day so lags mean what they say.
    full = pd.date_range(d.date.min(), d.date.max(), freq="D")
    d = d.set_index("date").reindex(full).rename_axis("date").reset_index()
    d["state"] = "Karnataka"

    d["lag_1"] = d.energy_met_mu.shift(1)
    d["lag_7"] = d.energy_met_mu.shift(7)
    d["roll_7"] = d.energy_met_mu.shift(1).rolling(7, min_periods=7).mean()

    d["dow"] = d.date.dt.dayofweek                 # 0 Monday
    d["day_name"] = d.date.dt.day_name()
    d["month"] = d.date.dt.month
    d["year"] = d.date.dt.year
    d["is_weekend"] = d.dow.isin([5, 6]).astype(int)
    d["t"] = (d.date - d.date.min()).dt.days       # linear trend in days

    ka = holidays.India(subdiv="KA", years=range(d.year.min(), d.year.max() + 1))
    d["holiday_name"] = d.date.dt.date.map(lambda x: ka.get(x))
    d["is_holiday"] = d.holiday_name.notna().astype(int)

    if WEATHER.exists():
        w = pd.read_csv(WEATHER, parse_dates=["date"])
        d = d.merge(w, on="date", how="left")
        status = f"joined {w.date.min().date()} to {w.date.max().date()}, {len(w):,} days"
        matched = d.temp_max_c.notna().sum()
        status += f", matched {matched:,} of {len(d):,} rows"
    else:
        for c in ["temp_max_c", "temp_min_c", "rain_mm"]:
            d[c] = np.nan
        status = "not run"
        print("no weather file found, weather columns left empty")

    (PROC / "weather_status.txt").write_text(status, encoding="utf-8")
    d.to_csv(OUT, index=False)

    have = d.energy_met_mu.notna().sum()
    print(f"wrote {OUT}")
    print(f"{len(d):,} calendar rows, {have:,} with demand, {len(d) - have} gaps")
    print(f"holidays flagged: {int(d.is_holiday.sum())} days")
    print(f"weather: {status}")


if __name__ == "__main__":
    main()
