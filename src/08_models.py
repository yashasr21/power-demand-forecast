"""
Three baselines, then three models, all scored on the same held-out window.

The split is by time and never shuffled. Shuffling a time series lets the model
learn from days that come after the ones it is predicting, which is the single
easiest way to produce a number you cannot reproduce in production.

Test window: the last 12 weeks of the series. Everything before it is training.

Every approach is scored on exactly the same set of test days. A day is only
scored if all six approaches could produce a number for it, so nobody gets a
free pass by quietly skipping the hard days.

Outputs
    data/processed/model_scores.csv
    data/processed/forecast_vs_actual.csv
    data/processed/worst_days.csv

Run:  python src/08_models.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
TEST_WEEKS = 12


def mae(a, p):
    return float(np.mean(np.abs(a - p)))


def mape(a, p):
    return float(np.mean(np.abs((a - p) / a)) * 100)


def design(df, lags=False, weather=False):
    """Calendar features. Monday and January are the dropped reference levels."""
    X = pd.DataFrame(index=df.index)
    for d in range(1, 7):
        X[f"dow_{d}"] = (df.dow == d).astype(int)
    for m in range(2, 13):
        X[f"month_{m}"] = (df.month == m).astype(int)
    X["is_holiday"] = df.is_holiday
    X["t"] = df.t
    if lags:
        X["lag_1"] = df.lag_1
        X["lag_7"] = df.lag_7
        X["roll_7"] = df.roll_7
    if weather:
        X["temp_max_c"] = df.temp_max_c
    return X


def main():
    d = pd.read_csv(PROC / "model_input.csv", parse_dates=["date"]).sort_values("date")
    have_weather = d.temp_max_c.notna().sum() > 100

    cutoff = d.date.max() - pd.Timedelta(weeks=TEST_WEEKS)
    train = d[(d.date <= cutoff) & d.energy_met_mu.notna()].copy()
    test = d[(d.date > cutoff) & d.energy_met_mu.notna()].copy()
    print(f"train {train.date.min().date()} to {train.date.max().date()}  {len(train):,} days")
    print(f"test  {test.date.min().date()} to {test.date.max().date()}  {len(test):,} days")
    print(f"weather in the model: {'yes' if have_weather else 'no, not fetched yet'}\n")

    pred = pd.DataFrame({"date": test.date.values, "actual": test.energy_met_mu.values})

    # ---- baselines -------------------------------------------------------
    pred["yesterday"] = test.lag_1.values
    pred["last_week"] = test.lag_7.values
    pred["trailing_7day"] = test.roll_7.values

    # ---- model 1: calendar only ------------------------------------------
    # Day of week, month, holiday flag, linear trend. No idea what yesterday
    # looked like. Kept in the results even though it does badly, because why
    # it does badly is the most useful thing in this file.
    fit_rows = train.dropna(subset=["energy_met_mu"])
    m1 = LinearRegression().fit(design(fit_rows), fit_rows.energy_met_mu)
    pred["calendar_only"] = m1.predict(design(test))

    # ---- model 2: calendar plus the recent level -------------------------
    # Same calendar features, plus yesterday, the same day last week, and the
    # trailing 7-day mean. This is the first model that knows where the series
    # currently sits rather than where an eleven-year trend line says it should.
    lag_train = fit_rows.dropna(subset=["lag_1", "lag_7", "roll_7"])
    m2 = LinearRegression().fit(design(lag_train, lags=True), lag_train.energy_met_mu)
    pred["calendar_plus_lags"] = m2.predict(design(test, lags=True))

    # ---- model 3: the same, plus temperature -----------------------------
    if have_weather:
        w_train = lag_train.dropna(subset=["temp_max_c"])
        m3 = LinearRegression().fit(
            design(w_train, lags=True, weather=True), w_train.energy_met_mu
        )
        pred["plus_temperature"] = m3.predict(design(test, lags=True, weather=True))
    else:
        pred["plus_temperature"] = np.nan

    # ---- model 4: SARIMAX with a weekly season ---------------------------
    # SARIMAX needs an unbroken daily index, so the 154 missing days are
    # linearly interpolated for this model only. That is a real assumption and
    # it is why this model is the one I trust least.
    try:
        from statsmodels.tsa.statespace.sarimax import SARIMAX

        y = (
            train.set_index("date").energy_met_mu
            .reindex(pd.date_range(train.date.min(), train.date.max(), freq="D"))
            .interpolate("linear")
        )
        y = y.tail(365 * 4)                       # four years is plenty and fits fast
        fit = SARIMAX(
            y, order=(2, 1, 1), seasonal_order=(1, 0, 1, 7),
            enforce_stationarity=False, enforce_invertibility=False,
        ).fit(disp=False, maxiter=120)
        horizon = (test.date.max() - train.date.max()).days
        fc = fit.forecast(steps=horizon)
        fc.index = pd.date_range(train.date.max() + pd.Timedelta(days=1), periods=horizon)
        pred["sarimax"] = pred.date.map(fc)
        print("SARIMAX(2,1,1)(1,0,1,7) fitted on the last four years\n")
    except Exception as e:                        # noqa: BLE001
        print(f"SARIMAX skipped: {e}\n")
        pred["sarimax"] = np.nan

    # ---- score, on identical rows ----------------------------------------
    approaches = [
        ("Yesterday", "yesterday", "baseline"),
        ("Same day last week", "last_week", "baseline"),
        ("Trailing 7-day average", "trailing_7day", "baseline"),
        ("Calendar only", "calendar_only", "model"),
        ("Calendar + lags", "calendar_plus_lags", "model"),
        ("Calendar + lags + temperature", "plus_temperature", "model"),
        ("SARIMAX weekly", "sarimax", "model"),
    ]
    usable = [c for _, c, _ in approaches if pred[c].notna().any()]
    common = pred.dropna(subset=usable + ["actual"])
    print(f"scoring every approach on the same {len(common)} days\n")

    rows = []
    for label, col, kind in approaches:
        if col not in usable:
            rows.append({"approach": label, "kind": kind, "mae_mu": None,
                         "mape_pct": None, "days_scored": 0,
                         "note": "not run - weather data not fetched"})
            continue
        rows.append({
            "approach": label, "kind": kind,
            "mae_mu": round(mae(common.actual, common[col]), 2),
            "mape_pct": round(mape(common.actual, common[col]), 2),
            "days_scored": len(common), "note": "",
        })
    scores = pd.DataFrame(rows)
    scores = scores.sort_values("mape_pct", na_position="last").reset_index(drop=True)
    scores.to_csv(PROC / "model_scores.csv", index=False)
    print(scores.to_string(index=False))

    best_base = scores[(scores.kind == "baseline")].mape_pct.min()
    best_model = scores[(scores.kind == "model")].mape_pct.min()
    winner = scores.iloc[0]
    print(f"\nbest baseline MAPE {best_base}%, best model MAPE {best_model}%")
    print(f"winner overall: {winner.approach} at {winner.mape_pct}%")
    if best_base <= best_model:
        print("A baseline beat every model. That is the finding, not a bug.")
    else:
        cut = (best_base - best_model) / best_base * 100
        print(f"The best model cuts baseline error by {cut:.1f}%.")

    pred.to_csv(PROC / "forecast_vs_actual.csv", index=False)

    # ---- where it went wrong ---------------------------------------------
    best_col = dict((l, c) for l, c, _ in approaches)[winner.approach]
    worst = common.assign(
        error_mu=(common[best_col] - common.actual).round(1),
        abs_pct=((common[best_col] - common.actual).abs() / common.actual * 100).round(2),
    ).nlargest(5, "abs_pct")[["date", "actual", best_col, "error_mu", "abs_pct"]]
    worst = worst.merge(d[["date", "day_name", "holiday_name"]], on="date", how="left")
    worst.to_csv(PROC / "worst_days.csv", index=False)
    print("\nfive worst days for the winning approach:")
    print(worst.to_string(index=False))


if __name__ == "__main__":
    main()
