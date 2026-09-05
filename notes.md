# Notes

Two lines per problem: what I tried, why it did not work, what I did instead.
Written as I went, so it runs oldest first and is not tidied up afterwards.

---

**Could not get the original PDFs.**
The plan was to pull the Grid-India daily load report PDFs, one per day, and
parse the state-wise table out of each. The archive was not reachable from the
machine I built this on. I used a published CSV extraction of the same daily
reports instead. That means the extraction step is somebody else's work and any
error in it passes straight into my analysis without me being able to see it.
Written up in `data/raw/SOURCE.md` with a ten-date spot-check plan against the
original PDFs. **Still to do: run those ten checks and record each one here,
pass or fail.**

**55 dates appear twice.**
First instinct was `drop_duplicates()` and move on. Checked before doing it:
45 of the 55 pairs are byte-identical rows, 10 disagree on the national Total,
and 6 of those 10 also disagree on Karnataka itself. Dropping blind would have picked whichever row happened to come first.
Rule I settled on: keep the row whose Total is closest to the sum of its own
state columns, on the reasoning that a row which adds up is more likely to be
the correctly parsed one. All 55 decisions are logged in
`data/processed/parse_failures.csv`, including which Total I kept and why.

**January to March 2013 is almost empty.**
82 of the first 90 days have no row at all. A series starting there would spend
its first quarter as interpolation dressed up as data. Cut the series to start
2013-04-01 and lost 63 rows. The trade is that the "eleven years" claim is
really eleven years and one month, and I say so rather than rounding it up.

**Lags were silently wrong the first time.**
I wrote `df.energy_met_mu.shift(1)` on the sorted frame and it looked fine. It
was not: with 154 missing days in the series, a row-based shift compares a
Tuesday to the previous Friday and calls it "yesterday". Fixed by reindexing
onto a complete calendar first, so a missing previous day produces an empty lag
and the model drops that row instead of learning from a lie. There is now a
quality check that recomputes `lag_1` and compares, so this cannot come back.

**Weather is not in yet.**
Open-Meteo's archive endpoint was blocked from the build machine. Rather than
substitute anything, `03_get_weather.py` exits with a message, the weather
columns stay empty, the weather model is reported as "not run" in the scoreboard
and the temperature quality check fails visibly. Everything downstream fills in
once the script runs from a machine with internet.
**Still to do: run `03_get_weather.py`, then 04, 05, 06, 08, 09 again.**

**The calendar model was terrible and that turned out to be the point.**
Day of week, month, holiday flag and a linear trend gave 16.42% MAPE. Repeating
yesterday's number gives 2.70%. My first thought was a bug. It is not: the model
knows what kind of day it is and nothing about what level the series is
currently at, so it extrapolates an eleven-year trend line into 2024 and lands
well below reality. Adding `lag_1`, `lag_7` and the trailing 7-day mean to the
same feature set took it to 1.80%. I kept the broken version in the results
table because the comparison explains more than the winner does on its own.

**SARIMAX needed a series that does not exist.**
It wants an unbroken daily index and the real one has 154 holes. Interpolated
the gaps linearly for that model only, and fitted on the last four years rather
than all eleven because the fit was slow and the early years are a different
regime anyway. It still scored 7.21%, worse than doing nothing clever. Two
assumptions stacked on top of each other is probably why, and it is the model I
trust least.

**Holiday effect looked bigger than it was.**
Comparing holidays against the overall daily average made them look very quiet.
Most of that was Sundays: a holiday landing on a Sunday is not evidence about
holidays. Recomputed against the same day of week within a 21-day window and the
effect dropped to about −2% on average, with Gandhi Jayanti, Dussehra and Diwali
the genuinely quiet ones. Same fix applied in `sql/06_holiday_effect.sql`, which
joins on year-month plus day name.

**Broken bar on the dashboard.**
The score chart drew a bar of width NaN for the weather model, which overlapped
the legend. Cause was `if r["mape"] is not None` — a pandas NaN is not None, so
the filter let it through. Changed to a self-comparison NaN check. Reminder that
"empty" has three different meanings in this stack and they are not
interchangeable.

**Dashboard spacing collapsed in one renderer.**
The header meta line ran together as one string when rendered outside a current
browser, because it relied on flexbox `gap`. Added margins on the child elements
as well, which costs nothing and means the page does not depend on one CSS
feature being supported.

**Bar charts do not start at zero.**
The weekday spread is 7.7%. On a zero-based axis it is seven bars of the same
height and the chart says nothing. Kept the cropped axis and wrote the crop into
the caption along with the actual spread, so the chart is readable and nobody is
misled by it.

---

## Things I know are still open

- Ten-date verification against the original Grid-India PDFs.
- Weather fetch, and everything that unlocks.
- One test window, 84 days, all of it pre-monsoon. A monsoon window would very
  likely rank the approaches differently and I have not checked.
- Daily energy only. Evening peak demand in MW is the number a grid operator
  actually plans against, and this project does not touch it.
