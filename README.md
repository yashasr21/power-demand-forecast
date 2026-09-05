# Forecasting daily electricity demand in Karnataka

**Dashboard:** https://yashasr21.github.io/power-demand-forecast/

## The question

A state grid operator has to decide, days in advance, how much power to buy. Buy
too little and there are outages; buy too much and the money is wasted. So: how
much power will Karnataka need tomorrow, and how badly does a simple guess beat
a real model?

## What I found

- **A model that ignores the recent level is useless.** Day of week, month,
  holidays and a trend line gave 16.42% average error. Repeating yesterday's
  number gives 2.70%. Adding yesterday, the same day last week and the trailing
  seven-day mean to the same calendar features took it to **1.80%**, a 33%
  improvement on the best simple rule.
- **The year matters more than the week.** March runs 43.2% above July, driven by
  pre-monsoon heat and irrigation pumping that both fall away when the rain
  arrives. The gap between the heaviest and lightest weekday is only 7.7%.
- **Demand grew 4.75% a year.** Average daily energy met went from 165.3 MU in
  2014 to 250.9 MU in 2023, up 51.8%. Karnataka is about 5.9% of all-India
  demand and that share has barely moved.
- **Festivals show up more clearly than weekends.** Against a normal day of the
  same weekday, Gandhi Jayanti runs 8.1% lower, Dussehra 7.7% and Diwali 5.9%.
  Across all 212 public holidays the average is only −2.0%.
- **The single heaviest day on record is 5 April 2024 at 336.9 MU**, inside a
  273-day unbroken run above the all-time average that starts in July 2023.

## The data

Grid Controller of India (formerly POSOCO) publishes a daily national and
state-wise load report. "Energy met" is the energy actually supplied to a state
over the day, in million units; one MU is one gigawatt-hour.

| | |
|---|---|
| Source | Grid-India daily load reports, via a published CSV extraction |
| Range | 2013-01-01 to 2024-04-28 |
| Raw rows | 3,955 |
| Usable Karnataka days | 3,892 of 4,046 calendar days (96.2%) |
| All-state long table | 130,524 rows across 34 states and territories |
| Problems logged | 210 entries in `data/processed/parse_failures.csv` |

**I did not parse the PDFs myself.** The PDF archive was not reachable from the
machine I built this on, so I used a published CSV extraction of the same daily
reports. The numbers are Grid-India's; the extraction step is somebody else's,
which means an extraction error would pass straight through into everything
here without being visible from inside the file. `data/raw/SOURCE.md` records
this along with a ten-date spot-check plan against the original PDFs. Those
checks are still outstanding and I have not claimed otherwise.

Nothing was cleaned silently. Every dropped, changed or flagged row is in
`parse_failures.csv` with a reason: 154 missing calendar days left as gaps
rather than interpolated, 55 duplicate dates resolved by keeping the row whose
national total is closest to the sum of its own state columns, and the first
quarter of 2013 cut because 82 of its 90 days were missing.

The quality gate in `src/05_quality_checks.py` runs 13 assertions and currently
passes 12. The one that fails is the temperature range check, which fails
because the weather fetch has not been run yet, not because the check was
removed. Report in `docs/quality_report.txt`.

## How to run it

```bash
pip install -r requirements.txt

python src/01_download.py          # fetch source, write provenance
python src/02_build_daily_table.py # clean, dedupe, log every failure
python src/03_get_weather.py       # Open-Meteo, no API key needed
python src/04_join.py              # lags, calendar, holidays, weather
python src/05_quality_checks.py    # 13 assertions, pass or fail
python src/06_explore.py           # the five questions
python src/07_load_sqlite.py       # build data/demand.db, run sql/*.sql
python src/08_models.py            # baselines and models, one scoreboard
python src/09_build_dashboard.py   # regenerate docs/index.html
```

Every number on the dashboard is read out of `data/processed` at build time, so
the page cannot drift away from the data. `.github/workflows/refresh.yml` runs
the whole thing weekly and commits anything that changed.

## How the forecast was tested

Split by date, never shuffled: training runs 2013-04-01 to 2024-02-04 (3,808
days) and the test window is the final 12 weeks, 2024-02-05 to 2024-04-28 (84
days). A day is only scored if every approach could produce a number for it, so
all seven are measured on exactly the same 84 days and nobody gets a free pass
by skipping the hard ones.

| Approach | Type | MAE (MU) | MAPE |
|---|---|---|---|
| Calendar + lags | model | 5.61 | **1.80%** |
| Yesterday | baseline | 8.37 | 2.70% |
| Same day last week | baseline | 8.39 | 2.71% |
| Trailing 7-day average | baseline | 8.57 | 2.77% |
| SARIMAX (2,1,1)(1,0,1,7) | model | 23.00 | 7.21% |
| Calendar only | model | 52.05 | 16.42% |
| Calendar + lags + temperature | model | — | not run yet |

MAPE is the headline because demand nearly quadrupled in range over the period
and a percentage stays comparable across that; MAE is there because 5.6 MU
missed on a 195 MU day is easier to picture than a percentage.

The winning model's five worst days all sit in the last fortnight of April, when
demand is climbing fastest ahead of the monsoon. Anything leaning on yesterday
is a step behind a rising series. Details in `data/processed/worst_days.csv`.

## What this does not tell you

- It forecasts energy over a whole day. A grid operator plans against the
  evening peak in MW, which this project does not touch at all.
- The source is a third-party extraction of the Grid-India PDFs and I have not
  yet verified it against the originals.
- The test window is 84 pre-monsoon days. A monsoon window would very plausibly
  rank these approaches differently and I have not checked.
- The weather model has not been run, so the question "does temperature add
  anything once you already know yesterday" is still open.
- Bengaluru's weather stands in for a state with coastal, plateau and hill
  districts. That is an assumption, not a finding.
- The linear regression assumes today's demand is a straight-line function of
  yesterday's. It holds well enough over 84 days; it would not hold through a
  structural break like the 2020 lockdown.

Dead ends, wrong turns and the reasoning behind each decision are in
[`notes.md`](notes.md).
