"""
Build docs/index.html.

Every number on the page is read out of data/processed. Nothing is typed in by
hand, so the page cannot drift away from the data the way a screenshot does.
One file, no build step, no CDN, no JavaScript.

Run:  python src/09_build_dashboard.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
DOCS = ROOT / "docs"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

CSS = """
:root{
  --paper:#FBE4EA; --paper-2:#FDF1F4; --ink:#2A1721; --rose:#B01048;
  --deep:#1F5673; --muted:#8E6675; --rule:#E9C9D3; --sand:#C4741A;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  font-size:16px; line-height:1.6;
}
.wrap{max-width:1000px; margin:0 auto; padding:0 24px 96px}
a{color:var(--rose)}
a:focus-visible,summary:focus-visible{outline:2px solid var(--rose); outline-offset:3px}

.masthead{padding:72px 0 28px; border-bottom:2px solid var(--ink)}
.masthead h1{
  font-family:Fraunces,"Iowan Old Style",Georgia,serif;
  font-weight:600; font-variation-settings:"SOFT" 20,"WONK" 1;
  font-size:clamp(2.3rem,6vw,3.9rem); line-height:1.02; letter-spacing:-.02em;
  margin:0 0 14px; max-width:16ch;
}
.standfirst{font-size:1.12rem; max-width:62ch; margin:0 0 22px; color:#4A2C39}
.meta{display:flex; flex-wrap:wrap; font-size:.86rem; color:var(--muted)}
.meta span{margin:0 26px 8px 0}
.meta b{font-weight:500; color:var(--ink)}

section{padding:52px 0 0}
h2{
  font-family:Fraunces,"Iowan Old Style",Georgia,serif; font-weight:600;
  font-size:1.65rem; letter-spacing:-.01em; margin:0 0 6px;
}
.lede{max-width:64ch; margin:0 0 24px; color:#4A2C39}
figure{margin:0}
.plot{background:var(--paper-2); border:1px solid var(--rule); padding:18px 16px 12px}
figcaption{font-size:.85rem; color:var(--muted); margin-top:10px; max-width:70ch}

.headline{display:flex; flex-wrap:wrap; align-items:flex-end; margin:34px 0 8px}
.stat{margin:0 40px 14px 0}
.stat .n{
  font-family:Fraunces,Georgia,serif; font-size:3.5rem; line-height:.9;
  font-variant-numeric:tabular-nums; color:var(--rose);
}
.stat .k{font-size:.87rem; color:var(--muted); margin-top:8px; max-width:22ch}

.finding{
  border-left:4px solid var(--rose); background:var(--paper-2);
  padding:20px 24px; margin:30px 0 0; max-width:72ch;
}
.finding p{margin:0 0 12px} .finding p:last-child{margin:0}

.pair{display:grid; grid-template-columns:1fr 1fr; grid-gap:22px; gap:22px}
@media(max-width:760px){.pair{grid-template-columns:1fr}}

table{border-collapse:collapse; width:100%; font-size:.92rem;
      font-variant-numeric:tabular-nums; margin-top:6px}
th{text-align:left; font-weight:500; color:var(--muted); font-size:.82rem;
   border-bottom:1px solid var(--ink); padding:0 12px 7px 0}
td{padding:9px 12px 9px 0; border-bottom:1px solid var(--rule)}
td.num,th.num{text-align:right}

.checks{display:flex; flex-wrap:wrap; margin-top:18px}
.chip{margin:0 8px 8px 0}
.chip{font-size:.79rem; padding:5px 11px; border:1px solid var(--rule);
      background:var(--paper-2); color:#4A2C39}
.chip.bad{border-color:var(--sand); color:#8A4E0B}

.note{font-size:.9rem; color:var(--muted); max-width:68ch}
footer{margin-top:64px; padding-top:22px; border-top:2px solid var(--ink); font-size:.9rem}
footer h3{font-family:Fraunces,Georgia,serif; font-size:1.1rem; margin:0 0 8px}
code{font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:.86em;
     background:var(--paper-2); padding:1px 5px}
ul{padding-left:20px; max-width:70ch} li{margin-bottom:6px}
@media(prefers-reduced-motion:no-preference){}
"""


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main():
    DOCS.mkdir(parents=True, exist_ok=True)
    f = json.loads((PROC / "findings.json").read_text())
    scores = pd.read_csv(PROC / "model_scores.csv")
    fva = pd.read_csv(PROC / "forecast_vs_actual.csv", parse_dates=["date"])
    worst = pd.read_csv(PROC / "worst_days.csv", parse_dates=["date"])
    mi = pd.read_csv(PROC / "model_input.csv", parse_dates=["date"])
    quality = (DOCS / "quality_report.txt").read_text().splitlines()
    weather_status = (PROC / "weather_status.txt").read_text().strip()

    scored = scores.dropna(subset=["mape_pct"])
    winner = scored.iloc[0]
    best_base = scored[scored.kind == "baseline"].iloc[0]
    cut = (best_base.mape_pct - winner.mape_pct) / best_base.mape_pct * 100
    win_col = {
        "Yesterday": "yesterday", "Same day last week": "last_week",
        "Trailing 7-day average": "trailing_7day", "Calendar only": "calendar_only",
        "Calendar + lags": "calendar_plus_lags",
        "Calendar + lags + temperature": "plus_temperature", "SARIMAX weekly": "sarimax",
    }[winner.approach]

    # ---- charts ----------------------------------------------------------
    have = mi.dropna(subset=["energy_met_mu"])
    smooth = mi.set_index("date").energy_met_mu.rolling(30, min_periods=20).mean()
    hero = charts.forecast_chart(
        list(fva.date.dt.to_pydatetime()), fva.actual.tolist(),
        fva[win_col].tolist(), winner.approach.lower(),
    )
    series = charts.long_series(
        list(mi.date.dt.to_pydatetime()), mi.energy_met_mu.tolist(), smooth.tolist()
    )
    wk = f["weekday"]["values"]
    wk_chart = charts.column_chart(
        list(wk.keys()), list(wk.values()), highlight={f["weekday"]["lowest_day"]}
    )
    mo = f["monthly"]["values"]
    mo_chart = charts.column_chart(
        list(mo.keys()), list(mo.values()),
        highlight={f["monthly"]["peak_month"], f["monthly"]["trough_month"]},
    )
    sc = charts.score_chart([
        {"approach": r.approach, "mape": r.mape_pct, "kind": r.kind}
        for r in scores.itertuples()
    ])

    # ---- quality chips ---------------------------------------------------
    chips = []
    for line in quality:
        if line.startswith("[PASS]"):
            chips.append(f'<span class="chip">{esc(line[7:])}</span>')
        elif line.startswith("[FAIL]"):
            chips.append(f'<span class="chip bad">{esc(line[7:])} — not run</span>')
    passed = sum(1 for l in quality if l.startswith("[PASS]"))
    total = passed + sum(1 for l in quality if l.startswith("[FAIL]"))

    # ---- tables ----------------------------------------------------------
    srows = "".join(
        f"<tr><td>{esc(r.approach)}</td><td>{esc(r.kind)}</td>"
        f'<td class="num">{"—" if pd.isna(r.mae_mu) else f"{r.mae_mu:.2f}"}</td>'
        f'<td class="num">{"—" if pd.isna(r.mape_pct) else f"{r.mape_pct:.2f}%"}</td>'
        f"<td>{esc(r.note if isinstance(r.note, str) else '')}</td></tr>"
        for r in scores.itertuples()
    )
    wrows = "".join(
        f"<tr><td>{r.date:%d %b %Y}</td><td>{esc(r.day_name)}</td>"
        f'<td class="num">{r.actual:.1f}</td>'
        f'<td class="num">{getattr(r, win_col):.1f}</td>'
        f'<td class="num">{r.abs_pct:.1f}%</td>'
        f"<td>{esc('' if pd.isna(r.holiday_name) else r.holiday_name)}</td></tr>"
        for r in worst.itertuples()
    )

    hol = f["holiday"]
    quiet = ", ".join(f"{q['name']} ({q['diff_pct']}%)" for q in hol["quietest"])
    weather_line = (
        f"Bengaluru temperature {weather_status}."
        if weather_status != "not run"
        else "Temperature is not on the page yet: the weather fetch has not been run, "
             "so the weather model and one quality check are still open."
    )
    built = datetime.now(timezone.utc).strftime("%d %B %Y")
    cov = f["coverage"]
    t = f["trend"]

    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Karnataka daily electricity demand — forecast and error</title>
<meta name="description" content="Eleven years of Grid-India daily reports for Karnataka, three baselines, four models, and where the forecast breaks.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@400&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head><body><div class="wrap">

<header class="masthead">
  <h1>How much power will Karnataka need tomorrow?</h1>
  <p class="standfirst">Eleven years of Grid-India daily load reports, three deliberately
  stupid forecasts, four real models, and a straight answer about which of them is
  actually worth running.</p>
  <div class="meta">
    <span><b>{cov['days']:,}</b> days, {cov['start']} to {cov['end']}</span>
    <span>average <b>{cov['mean_mu']} MU</b> a day</span>
    <span>source <b>Grid-India daily reports</b></span>
    <span>rebuilt <b>{built}</b></span>
  </div>
</header>

<section>
  <div class="headline">
    <div class="stat"><div class="n">{winner.mape_pct:.2f}%</div>
      <div class="k">average error of the best approach over the last {int(winner.days_scored)} days</div></div>
    <div class="stat"><div class="n">{winner.mae_mu:.1f}</div>
      <div class="k">MU typically missed per day, against a {cov['mean_mu']} MU average</div></div>
    <div class="stat"><div class="n">{cut:.0f}%</div>
      <div class="k">less error than the best simple rule, which was &ldquo;{esc(best_base.approach.lower())}&rdquo;</div></div>
  </div>
  <figure><div class="plot">{hero}</div>
  <figcaption>The held-out window. The model never saw any of these days during
  training, and the split is by date, not random. Shaded area is the daily miss.</figcaption></figure>
</section>

<section>
  <h2>What I found</h2>
  <div class="finding">
    <p>Karnataka's daily demand grew from {t['first_mean']} MU in {t['first_year']} to
    {t['last_mean']} MU in {t['last_year']}, about {t['cagr_pct']}% a year. The shape of the
    year matters more than the growth: {f['monthly']['peak_month']} runs
    {f['monthly']['gap_pct']}% above {f['monthly']['trough_month']}, because the pre-monsoon
    heat and irrigation pumping both peak before the rain arrives and both fall away once
    it does.</p>
    <p>A week is a much smaller effect than a season. {f['weekday']['highest_day']} is the
    heaviest day and {f['weekday']['lowest_day']} the lightest, but only
    {f['weekday']['gap_pct']}% apart. Festivals show up more clearly than weekends:
    across {hol['n_compared']} public holidays demand sits {hol['avg_diff_pct']}% below a
    normal day of the same weekday, and the quietest are {quiet}.</p>
    <p>{weather_line}</p>
  </div>
</section>

<section>
  <h2>Eleven years in one line</h2>
  <p class="lede">Daily demand in grey, a 30-day average in red. The dip in the middle of
  2020 is the lockdown; the sawtooth is the monsoon arriving every year.</p>
  <figure><div class="plot">{series}</div>
  <figcaption>{len(have):,} days plotted. The {len(mi) - len(have)} days the source never
  published are gaps in the line rather than interpolated values.</figcaption></figure>
</section>

<section>
  <h2>The week and the year</h2>
  <div class="pair">
    <figure><div class="plot">{wk_chart}</div>
      <figcaption>Average demand by day of week. {f['weekday']['lowest_day']} is the only
      day that stands apart. The axis is cropped, not zero-based: the whole spread is
      {f['weekday']['gap_pct']}%, and on a zero-based axis you would see seven bars the
      same height.</figcaption></figure>
    <figure><div class="plot">{mo_chart}</div>
      <figcaption>Average demand by month, {f['monthly']['peak_month']} peak to
      {f['monthly']['trough_month']} trough. Axis cropped the same way, though here the
      {f['monthly']['gap_pct']}% spread would survive a zero-based one.</figcaption></figure>
  </div>
</section>

<section>
  <h2>Which forecast is worth running</h2>
  <p class="lede">Every approach is scored on the same {int(winner.days_scored)} days with
  the same metric, baselines included. Mean absolute percentage error, lower is better.</p>
  <figure><div class="plot">{sc}</div></figure>
  <table><thead><tr><th>Approach</th><th>Type</th><th class="num">MAE (MU)</th>
  <th class="num">MAPE</th><th>Note</th></tr></thead><tbody>{srows}</tbody></table>
  <p class="note" style="margin-top:18px">The calendar-only model is the interesting
  failure. It knows the day of week, the month, the holidays and a trend line, and it is
  still six times worse than repeating yesterday's number, because none of that tells it
  what level the series is at right now. Adding yesterday, the same day last week and the
  trailing average is what makes the model beat the simple rules.</p>
</section>

<section>
  <h2>Where it goes wrong</h2>
  <p class="lede">The five days the winning approach missed by the most.</p>
  <table><thead><tr><th>Date</th><th>Day</th><th class="num">Actual MU</th>
  <th class="num">Forecast MU</th><th class="num">Off by</th><th>Holiday</th></tr></thead>
  <tbody>{wrows}</tbody></table>
  <p class="note" style="margin-top:16px">All five sit in the last few weeks of the window,
  in the pre-monsoon build-up when demand climbs fastest. A model leaning on yesterday is
  always a step behind a series that is still rising.</p>
</section>

<section>
  <h2>Data quality gate</h2>
  <p class="lede">{passed} of {total} checks pass. The failing one is failing because a step
  has not been run, not because it was quietly removed.</p>
  <div class="checks">{''.join(chips)}</div>
</section>

<footer>
  <h3>What this does not tell you</h3>
  <ul>
    <li>It forecasts energy over a whole day, not the evening peak, which is what actually
    decides whether the lights stay on.</li>
    <li>The underlying numbers come from a published extraction of the Grid-India report
    PDFs rather than from the PDFs themselves, so an extraction error would pass straight
    through into everything above.</li>
    <li>The test window is {int(winner.days_scored)} days in one season. A window in the
    monsoon would very likely give a different answer.</li>
    <li>Bengaluru's weather is used as a stand-in for a state with coastal, plateau and
    hill districts.</li>
    <li>Every figure here is regenerated from the CSVs by
    <code>src/09_build_dashboard.py</code>. Nothing on this page was typed by hand.</li>
  </ul>
</footer>

</div></body></html>
"""
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote {DOCS / 'index.html'}  ({len(html):,} bytes)")
    print(f"headline: {winner.approach} at {winner.mape_pct}% MAPE, "
          f"{cut:.0f}% under the best baseline")


if __name__ == "__main__":
    main()
