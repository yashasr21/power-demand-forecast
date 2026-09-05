"""
Turn the raw wide table into one clean daily series for Karnataka.

Every row that gets dropped, changed or flagged is written to
data/processed/parse_failures.csv with a reason. Nothing is fixed silently.

Outputs
    data/processed/daily_demand.csv   date, state, energy_met_mu  (Karnataka)
    data/processed/state_daily.csv    long form, all states, for the SQL layer
    data/processed/parse_failures.csv every problem and what I did about it

Run:  python src/02_build_daily_table.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "daily_energy_met_MU.csv"
OUT = ROOT / "data" / "processed"

STATE = "Karnataka"

# Territories that are never on the national grid, so an empty cell is correct
# and not a parse failure.
OFF_GRID = ["Andaman and Nicobar Islands", "Lakshadweep"]

# Not a state. AMNSIL is a captive industrial supply, DVC is a generating
# corporation, Total is the national sum. None belong in a state table.
NOT_A_STATE = ["AMNSIL", "Damodar Valley Corporation", "Total"]

# 2013 Q1 is 82 days short out of 90. A series that starts there would spend
# its first quarter interpolating, so the series starts in April instead.
SERIES_START = "2013-04-01"

failures = []


def log(date, kind, detail, action):
    failures.append(
        {"date": date, "problem": kind, "detail": detail, "what_i_did": action}
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(RAW, parse_dates=["Date"])
    print(f"read {len(raw):,} rows, {raw.Date.min().date()} to {raw.Date.max().date()}")

    state_cols = [
        c for c in raw.columns if c not in ["Date"] + NOT_A_STATE + OFF_GRID
    ]

    # ---- duplicate dates -------------------------------------------------
    # 49 of the 55 duplicated dates are identical rows and can just be
    # collapsed. The other 6 disagree on the national Total. For those I keep
    # the row whose Total is closest to the sum of its own state columns,
    # because a row that adds up is more likely to be the correctly parsed one.
    dupes = raw[raw.Date.duplicated(keep=False)]
    keep_idx = []
    for date, block in dupes.groupby("Date"):
        vals = block[state_cols + ["Total"]]
        if vals.duplicated(keep=False).all() and len(vals.drop_duplicates()) == 1:
            keep_idx.append(block.index[0])
            log(date.date(), "duplicate date", "identical rows", "kept the first")
        else:
            gap = (block[state_cols].sum(axis=1) - block["Total"]).abs()
            winner = gap.idxmin()
            keep_idx.append(winner)
            log(
                date.date(),
                "duplicate date, values disagree",
                f"totals {sorted(block.Total.round(1).tolist())}, "
                f"row sums off by {sorted(gap.round(1).tolist())}",
                f"kept Total={block.loc[winner, 'Total']:.1f}, the one closest to its own row sum",
            )
    drop_idx = set(dupes.index) - set(keep_idx)
    df = raw.drop(index=list(drop_idx)).sort_values("Date").reset_index(drop=True)
    print(f"dropped {len(drop_idx)} duplicate rows, {len(df):,} left")

    # ---- trim the ragged start ------------------------------------------
    before = len(df)
    df = df[df.Date >= SERIES_START]
    log(
        SERIES_START,
        "ragged start",
        "Jan-Mar 2013 has 82 of 90 days missing",
        f"cut the series to start {SERIES_START}, lost {before - len(df)} rows",
    )

    # ---- missing calendar days ------------------------------------------
    full = pd.date_range(df.Date.min(), df.Date.max(), freq="D")
    gaps = sorted(set(full) - set(df.Date))
    for d in gaps:
        log(d.date(), "missing day", "no row published for this date", "left as a gap, not interpolated")
    print(f"{len(gaps)} calendar days still missing after the trim")

    # ---- the Karnataka series -------------------------------------------
    ka = df[["Date", STATE]].rename(columns={"Date": "date", STATE: "energy_met_mu"})
    n_null = ka.energy_met_mu.isna().sum()
    n_bad = (ka.energy_met_mu <= 0).sum()
    for d in ka.loc[ka.energy_met_mu.isna(), "date"]:
        log(d.date(), "null demand", f"{STATE} cell empty", "row dropped")
    for d in ka.loc[ka.energy_met_mu <= 0, "date"]:
        log(d.date(), "impossible demand", "value <= 0 MU", "row dropped")
    ka = ka[ka.energy_met_mu.notna() & (ka.energy_met_mu > 0)]
    ka["state"] = STATE
    ka = ka[["date", "state", "energy_met_mu"]]

    # ---- long form, every state, for SQL --------------------------------
    long = df.melt(
        id_vars="Date", value_vars=state_cols, var_name="state", value_name="energy_met_mu"
    ).rename(columns={"Date": "date"})
    empty_states = [
        s for s in state_cols if long.loc[long.state == s, "energy_met_mu"].isna().all()
    ]
    for s in empty_states:
        log("all", "state empty throughout", s, "kept the column, flagged here")
    long = long.dropna(subset=["energy_met_mu"])
    long = long[long.energy_met_mu > 0]

    ka.to_csv(OUT / "daily_demand.csv", index=False)
    long.to_csv(OUT / "state_daily.csv", index=False)
    pd.DataFrame(failures).to_csv(OUT / "parse_failures.csv", index=False)

    attempted = len(full)
    print(f"\n{STATE}: {len(ka):,} usable days out of {attempted:,} calendar days "
          f"({len(ka) / attempted:.1%})")
    print(f"nulls dropped {n_null}, impossible values dropped {n_bad}")
    print(f"all states long table: {len(long):,} rows, {long.state.nunique()} states")
    print(f"{len(failures)} entries in parse_failures.csv")


if __name__ == "__main__":
    main()
