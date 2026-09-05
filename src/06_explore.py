"""
Look at the series before modelling anything.

Five questions, answered in plain English at the end of the run and saved to
data/processed/findings.json so the README and the dashboard both read the same
numbers instead of me retyping them.

Outputs
    data/processed/yearly.csv, weekday.csv, monthly.csv, holiday_effect.csv
    data/processed/findings.json

Run:  python src/06_explore.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    d = pd.read_csv(PROC / "model_input.csv", parse_dates=["date"])
    d = d[d.energy_met_mu.notna()].copy()
    f = {}

    # 1. trend
    yearly = d.groupby("year").energy_met_mu.agg(["mean", "min", "max", "count"]).round(1)
    yearly = yearly[yearly["count"] >= 300]          # ignore part years at each end
    yearly.to_csv(PROC / "yearly.csv")
    first_y, last_y = yearly.index[0], yearly.index[-1]
    first_v, last_v = yearly.loc[first_y, "mean"], yearly.loc[last_y, "mean"]
    years = last_y - first_y
    cagr = (last_v / first_v) ** (1 / years) - 1
    f["trend"] = {
        "first_year": int(first_y), "last_year": int(last_y),
        "first_mean": float(first_v), "last_mean": float(last_v),
        "growth_pct": round((last_v / first_v - 1) * 100, 1),
        "cagr_pct": round(cagr * 100, 2),
    }

    # 2. weekday
    wk = d.groupby("day_name").energy_met_mu.mean().reindex(DAY_ORDER).round(1)
    wk.to_csv(PROC / "weekday.csv")
    f["weekday"] = {
        "values": {k: float(v) for k, v in wk.items()},
        "lowest_day": wk.idxmin(), "highest_day": wk.idxmax(),
        "gap_pct": round((wk.max() / wk.min() - 1) * 100, 1),
    }

    # 3. month
    mo = d.groupby("month").energy_met_mu.mean().round(1)
    mo.index = [MONTHS[i - 1] for i in mo.index]
    mo.to_csv(PROC / "monthly.csv")
    f["monthly"] = {
        "values": {k: float(v) for k, v in mo.items()},
        "peak_month": mo.idxmax(), "trough_month": mo.idxmin(),
        "gap_pct": round((mo.max() / mo.min() - 1) * 100, 1),
    }

    # 4. holidays. Compared against the same weekday within 21 days, because a
    #    holiday that lands on a Sunday is not evidence that holidays are quiet.
    d = d.sort_values("date")
    hol = d[d.is_holiday == 1]
    rows = []
    for _, r in hol.iterrows():
        window = d[
            (d.date.between(r.date - pd.Timedelta(days=21), r.date + pd.Timedelta(days=21)))
            & (d.dow == r.dow) & (d.is_holiday == 0)
        ]
        if len(window) >= 3:
            rows.append({
                "date": r.date.date(), "holiday": r.holiday_name,
                "demand": r.energy_met_mu, "normal": round(window.energy_met_mu.mean(), 1),
                "diff_pct": round((r.energy_met_mu / window.energy_met_mu.mean() - 1) * 100, 1),
            })
    he = pd.DataFrame(rows)
    he.to_csv(PROC / "holiday_effect.csv", index=False)
    by_name = he.groupby("holiday").diff_pct.agg(["mean", "count"]).round(1)
    by_name = by_name[by_name["count"] >= 5].sort_values("mean")
    f["holiday"] = {
        "n_compared": int(len(he)),
        "avg_diff_pct": round(float(he.diff_pct.mean()), 1),
        "quietest": [
            {"name": i, "diff_pct": float(r["mean"]), "n": int(r["count"])}
            for i, r in by_name.head(3).iterrows()
        ],
    }

    # 5. weather
    if d.temp_max_c.notna().sum() > 100:
        sub = d.dropna(subset=["temp_max_c"])
        r = sub.energy_met_mu.corr(sub.temp_max_c)
        hot = sub[sub.temp_max_c >= sub.temp_max_c.quantile(0.9)].energy_met_mu.mean()
        mild = sub[sub.temp_max_c <= sub.temp_max_c.quantile(0.5)].energy_met_mu.mean()
        f["weather"] = {
            "status": "joined", "n": int(len(sub)), "corr": round(float(r), 3),
            "hot_day_mean": round(float(hot), 1), "mild_day_mean": round(float(mild), 1),
            "uplift_pct": round((hot / mild - 1) * 100, 1),
        }
    else:
        f["weather"] = {"status": "not run"}

    f["coverage"] = {
        "days": int(len(d)),
        "start": str(d.date.min().date()), "end": str(d.date.max().date()),
        "mean_mu": round(float(d.energy_met_mu.mean()), 1),
    }
    (PROC / "findings.json").write_text(json.dumps(f, indent=2), encoding="utf-8")

    t = f["trend"]
    print(f"1. Average daily demand went from {t['first_mean']} MU in {t['first_year']} "
          f"to {t['last_mean']} MU in {t['last_year']}, up {t['growth_pct']}% "
          f"({t['cagr_pct']}% a year).")
    w = f["weekday"]
    print(f"2. {w['lowest_day']} is the quietest day and {w['highest_day']} the busiest, "
          f"a gap of {w['gap_pct']}%.")
    m = f["monthly"]
    print(f"3. Demand peaks in {m['peak_month']} and bottoms out in {m['trough_month']}, "
          f"{m['gap_pct']}% apart.")
    h = f["holiday"]
    print(f"4. Across {h['n_compared']} holidays, demand sits {h['avg_diff_pct']}% off a "
          f"normal same-weekday. Quietest: "
          + ", ".join(f"{q['name']} {q['diff_pct']}%" for q in h["quietest"]) + ".")
    if f["weather"]["status"] == "joined":
        we = f["weather"]
        print(f"5. Demand and max temperature correlate at r={we['corr']}; the hottest "
              f"10% of days run {we['uplift_pct']}% above a median day.")
    else:
        print("5. Weather not fetched yet, so the temperature question is unanswered.")


if __name__ == "__main__":
    main()
