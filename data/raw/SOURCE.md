# Where this data came from

**File:** `daily_energy_met_MU.csv`
**Downloaded:** 2026-09-07
**Fetched from:** https://raw.githubusercontent.com/tanshah0509-dotcom/India-Electricity-Demand-Forecasting/main/Data/daily_energy_met_MU.csv
**md5:** `c6d677992d4cf6735d09b71823140468`
**Size:** 815,685 bytes, 3,956 lines
**Covers:** 2013-01-01 to 2024-04-28, daily energy met in million units (MU),
one column per state and union territory, plus a national Total column.

## Original publisher

Grid Controller of India Ltd (Grid-India), formerly the Power System Operation
Corporation (POSOCO). Grid-India publishes a daily national and state-wise load
report as a PDF, one file per day, on the National Load Despatch Centre site.
"Energy met" is the energy actually supplied to a state over the day, in MU.
One MU is one gigawatt-hour.

## Why a CSV and not the PDFs

The PDF archive was not reachable from the environment this pipeline was built
in, so I used a published extraction of the same daily reports. The numbers are
the daily reports' numbers; the extraction step is somebody else's.

That is a real weakness and I have not hidden it. Two consequences:

1. Anything wrong in the extraction is now wrong in my analysis, and I cannot
   see it from inside the CSV.
2. The verification below is not optional, it is the thing that makes this
   source usable.

## Verification plan

Pick ten dates at random across the eleven years, open the matching Grid-India
daily report PDF, and compare the Karnataka energy-met figure and the national
Total against this file. Record every check, pass or fail, in `notes.md`.
Ten dates out of 3,955 is a spot check, not a proof, and I say so in the
README rather than claiming the file is verified.

## Known problems in the raw file, found before any analysis

- 55 dates appear twice. 45 of those pairs are identical rows; 10 disagree on
  the national Total, and 6 of those also disagree on the Karnataka figure.
- 181 calendar days are missing between the first and last date. 94 of them
  fall in 2013 and 82 of those are in January to March 2013.
- Andaman and Nicobar Islands and Lakshadweep are empty for every row. They are
  not on the national grid, so this is expected rather than broken.
- Telangana is empty for the first 423 days. Telangana was formed in June 2014,
  so this is also expected.
- Dadra and Nagar Haveli and Daman and Diu go empty for the last 695 days,
  around the point the two territories were merged.
- One Chhattisgarh cell is empty with no obvious reason.

`src/02_build_daily_table.py` handles each of these explicitly and logs what it
did rather than dropping rows quietly.
