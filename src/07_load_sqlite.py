"""
Load the processed tables into SQLite and run every query in sql/.

The database is rebuilt from scratch each run so it never drifts from the CSVs.
It is listed in .gitignore: the CSVs are the source of truth, the .db is just
something you can regenerate in four seconds.

Outputs
    data/demand.db
    data/processed/sql_results/*.csv   first 200 rows of each query

Run:  python src/07_load_sqlite.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
DB = ROOT / "data" / "demand.db"
SQL_DIR = ROOT / "sql"
RESULTS = PROC / "sql_results"


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()

    con = sqlite3.connect(DB)
    daily = pd.read_csv(PROC / "model_input.csv")
    states = pd.read_csv(PROC / "state_daily.csv")
    daily.to_sql("daily", con, index=False)
    states.to_sql("state_daily", con, index=False)
    con.execute("CREATE INDEX idx_daily_date ON daily(date)")
    con.execute("CREATE INDEX idx_state_date ON state_daily(date, state)")
    con.commit()
    print(f"loaded daily ({len(daily):,} rows) and state_daily ({len(states):,} rows)")

    for path in sorted(SQL_DIR.glob("*.sql")):
        query = path.read_text(encoding="utf-8")
        try:
            out = pd.read_sql_query(query, con)
        except Exception as e:                       # noqa: BLE001
            print(f"  {path.name} FAILED: {e}")
            continue
        out.head(200).to_csv(RESULTS / f"{path.stem}.csv", index=False)
        print(f"  {path.name:<34} {len(out):>6,} rows")
        if len(out):
            print("      " + out.head(2).to_string(index=False).replace("\n", "\n      "))

    con.close()
    print(f"\ndatabase at {DB}, results in {RESULTS}")


if __name__ == "__main__":
    main()
