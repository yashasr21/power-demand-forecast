"""
The quality gate. Thirteen checks against model_input.csv.

Failing checks do not stop the pipeline. They print, they go in the report, and
they go in the README. A check that silently passes because I weakened it is
worse than a check that fails and gets explained, so the thresholds here are
the ones I would defend out loud.

Output
    docs/quality_report.txt

Run:  python src/05_quality_checks.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "processed" / "model_input.csv"
OUT = ROOT / "docs" / "quality_report.txt"

results = []


def check(name, ok, detail):
    results.append({"check": name, "pass": bool(ok), "detail": detail})
    print(f"[{'pass' if ok else 'FAIL'}] {name} — {detail}")


def main():
    d = pd.read_csv(IN, parse_dates=["date"])
    got = d[d.energy_met_mu.notna()]

    n_dupes = d.date.duplicated().sum()
    check("no duplicate dates", n_dupes == 0, f"{n_dupes} repeated dates")

    full = pd.date_range(d.date.min(), d.date.max(), freq="D")
    check(
        "date index is a complete calendar",
        len(d) == len(full),
        f"{len(d):,} rows against {len(full):,} calendar days",
    )

    cover = len(got) / len(full)
    check(
        "demand present on at least 95% of days",
        cover >= 0.95,
        f"{len(got):,} of {len(full):,} days, {cover:.1%}",
    )

    check(
        "all demand values positive",
        (got.energy_met_mu > 0).all(),
        f"minimum {got.energy_met_mu.min():.1f} MU",
    )

    lo, hi = 60, 500
    out_of_band = got[(got.energy_met_mu < lo) | (got.energy_met_mu > hi)]
    check(
        f"demand inside a plausible {lo}-{hi} MU band for Karnataka",
        out_of_band.empty,
        f"{len(out_of_band)} days outside, observed range "
        f"{got.energy_met_mu.min():.1f} to {got.energy_met_mu.max():.1f} MU",
    )

    jump = got.set_index("date").energy_met_mu.pct_change().abs()
    big = jump[jump > 0.40]
    check(
        "no day-on-day jump over 40%",
        big.empty,
        f"{len(big)} such days"
        + (f", worst {big.max():.0%} on {big.idxmax().date()}" if len(big) else ""),
    )

    longest = 0
    run = 0
    for v in d.energy_met_mu.isna():
        run = run + 1 if v else 0
        longest = max(longest, run)
    check(
        "no gap longer than 10 consecutive days",
        longest <= 10,
        f"longest run of missing days is {longest}",
    )

    check(
        "every weekday appears a similar number of times",
        got.day_name.value_counts().std() < 20,
        f"spread across weekdays is {got.day_name.value_counts().std():.1f} days",
    )

    check(
        "holiday flag is set on a believable number of days",
        200 <= d.is_holiday.sum() <= 350,
        f"{int(d.is_holiday.sum())} holiday days over {d.year.nunique()} years",
    )

    check(
        "Republic Day is flagged every year it appears",
        d[(d.date.dt.month == 1) & (d.date.dt.day == 26)].is_holiday.all(),
        "spot check on a date I know is a holiday",
    )

    lag_ok = (
        d.loc[d.lag_1.notna(), "lag_1"]
        .reset_index(drop=True)
        .equals(d.energy_met_mu.shift(1).loc[d.lag_1.notna()].reset_index(drop=True))
    )
    check("lag_1 really is the previous calendar day", lag_ok, "recomputed and compared")

    check(
        "trend column increases by exactly one per day",
        (d.t.diff().dropna() == 1).all(),
        "no skipped days in the trend counter",
    )

    if d.temp_max_c.notna().any():
        t = d.temp_max_c.dropna()
        check(
            "Bengaluru max temperature inside 15-45 C",
            t.between(15, 45).all(),
            f"observed {t.min():.1f} to {t.max():.1f} C",
        )
    else:
        check(
            "Bengaluru max temperature inside 15-45 C",
            False,
            "weather not fetched yet, so this check could not run",
        )

    passed = sum(r["pass"] for r in results)
    lines = [
        "Data quality gate — Karnataka daily demand",
        f"input: {IN.name}",
        f"rows: {len(d):,}   days with demand: {len(got):,}",
        f"result: {passed} of {len(results)} checks passed",
        "",
    ]
    for r in results:
        lines.append(f"[{'PASS' if r['pass'] else 'FAIL'}] {r['check']}")
        lines.append(f"       {r['detail']}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n{passed} of {len(results)} passed. report at {OUT}")


if __name__ == "__main__":
    main()
