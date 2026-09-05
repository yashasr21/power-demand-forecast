"""
Hand-rolled SVG charts.

I did not want a charting library on the dashboard. A library means a CDN, a
CDN means the page breaks the day the CDN moves, and the whole point of the
dashboard is that it keeps working. These functions write SVG strings straight
into the HTML, so the page is one file with nothing to fetch.

Everything is drawn in a 0..W by 0..H user space and scaled by the browser
through viewBox, so the charts stay sharp at any width.
"""

from datetime import date

INK = "#2A1721"
ROSE = "#B01048"
DEEP = "#1F5673"
MUTED = "#B98A99"
RULE = "#E9C9D3"
SAND = "#C4741A"


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _open(w, h, label):
    return (
        f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" '
        f'aria-label="{_esc(label)}" xmlns="http://www.w3.org/2000/svg" '
        f'preserveAspectRatio="xMidYMid meet" font-family="IBM Plex Sans, sans-serif">'
    )


def _grid(x0, x1, y0, y1, lo, hi, ticks, fmt="{:.0f}"):
    out = []
    for i in range(ticks + 1):
        v = lo + (hi - lo) * i / ticks
        y = y1 - (y1 - y0) * i / ticks
        out.append(
            f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" '
            f'stroke="{RULE}" stroke-width="1"/>'
        )
        out.append(
            f'<text x="{x0 - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="11" '
            f'fill="{MUTED}" style="font-variant-numeric:tabular-nums">{fmt.format(v)}</text>'
        )
    return "".join(out)


def long_series(dates, values, smooth, title_y="MU per day"):
    """Eleven years of daily demand, with a 30-day mean drawn over the top."""
    W, H = 940, 330
    x0, x1, y0, y1 = 54, W - 14, 20, H - 34
    lo, hi = 90, 350
    n = len(values)

    def px(i):
        return x0 + (x1 - x0) * i / (n - 1)

    def py(v):
        return y1 - (y1 - y0) * (v - lo) / (hi - lo)

    s = [_open(W, H, "Daily electricity demand in Karnataka, 2013 to 2024")]
    s.append(_grid(x0, x1, y0, y1, lo, hi, 4))

    thin = " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(values) if v == v)
    s.append(f'<polyline points="{thin}" fill="none" stroke="{MUTED}" '
             f'stroke-width="0.7" opacity="0.75"/>')
    thick = " ".join(
        f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(smooth) if v == v
    )
    s.append(f'<polyline points="{thick}" fill="none" stroke="{ROSE}" '
             f'stroke-width="2.2" stroke-linejoin="round"/>')

    years = sorted({d.year for d in dates})
    for yr in years:
        try:
            i = next(k for k, d in enumerate(dates) if d.year == yr)
        except StopIteration:
            continue
        x = px(i)
        s.append(f'<line x1="{x:.1f}" y1="{y0}" x2="{x:.1f}" y2="{y1}" '
                 f'stroke="{RULE}" stroke-width="1" stroke-dasharray="2 4"/>')
        s.append(f'<text x="{x:.1f}" y="{y1 + 18}" text-anchor="middle" font-size="11" '
                 f'fill="{MUTED}">{yr}</text>')

    s.append(f'<text x="{x0}" y="{y0 - 6}" font-size="11" fill="{MUTED}">{title_y}</text>')
    s.append("</svg>")
    return "".join(s)


def forecast_chart(dates, actual, predicted, label):
    """The held-out window: what happened, and what the model said would happen."""
    W, H = 940, 340
    x0, x1, y0, y1 = 54, W - 14, 24, H - 40
    vals = [v for v in list(actual) + list(predicted) if v == v]
    lo = min(vals) * 0.96
    hi = max(vals) * 1.03
    n = len(actual)

    def px(i):
        return x0 + (x1 - x0) * i / (n - 1)

    def py(v):
        return y1 - (y1 - y0) * (v - lo) / (hi - lo)

    s = [_open(W, H, "Forecast against actual demand over the held-out weeks")]
    s.append(_grid(x0, x1, y0, y1, lo, hi, 4))

    band = []
    band += [f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(actual)]
    band += [f"{px(i):.1f},{py(v):.1f}" for i, v in reversed(list(enumerate(predicted)))]
    s.append(f'<polygon points="{" ".join(band)}" fill="{SAND}" opacity="0.16"/>')

    s.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.4" '
             'stroke-linejoin="round"/>'
             % (" ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(actual)), INK))
    s.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.2" '
             'stroke-dasharray="6 4" stroke-linejoin="round"/>'
             % (" ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(predicted)), ROSE))

    step = max(1, n // 6)
    for i in range(0, n, step):
        s.append(f'<text x="{px(i):.1f}" y="{y1 + 18}" text-anchor="middle" '
                 f'font-size="11" fill="{MUTED}">{dates[i].strftime("%d %b")}</text>')

    s.append(f'<g transform="translate({x0},{H - 8})" font-size="12">')
    s.append(f'<line x1="0" y1="-4" x2="22" y2="-4" stroke="{INK}" stroke-width="2.4"/>')
    s.append(f'<text x="28" y="0" fill="{INK}">actual</text>')
    s.append(f'<line x1="92" y1="-4" x2="114" y2="-4" stroke="{ROSE}" stroke-width="2.2" '
             f'stroke-dasharray="6 4"/>')
    s.append(f'<text x="120" y="0" fill="{INK}">{_esc(label)}</text>')
    s.append("</g></svg>")
    return "".join(s)


def column_chart(labels, values, highlight=None, unit="MU", fmt="{:.0f}"):
    """Weekday and month profiles."""
    W, H = 450, 240
    x0, x1, y0, y1 = 44, W - 12, 18, H - 36
    lo = min(values) * 0.97
    hi = max(values) * 1.01
    n = len(values)
    slot = (x1 - x0) / n
    bw = slot * 0.62

    def py(v):
        return y1 - (y1 - y0) * (v - lo) / (hi - lo)

    s = [_open(W, H, "Average demand by " + ("weekday" if n == 7 else "month"))]
    s.append(_grid(x0, x1, y0, y1, lo, hi, 3))
    for i, (lab, v) in enumerate(zip(labels, values)):
        x = x0 + slot * i + (slot - bw) / 2
        fill = ROSE if (highlight and lab in highlight) else DEEP
        op = "1" if (highlight and lab in highlight) else "0.55"
        s.append(f'<rect x="{x:.1f}" y="{py(v):.1f}" width="{bw:.1f}" '
                 f'height="{y1 - py(v):.1f}" fill="{fill}" opacity="{op}" rx="1.5"/>')
        s.append(f'<text x="{x + bw / 2:.1f}" y="{y1 + 16}" text-anchor="middle" '
                 f'font-size="10.5" fill="{MUTED}">{_esc(lab[:3])}</text>')
    s.append(f'<text x="{x0}" y="{y0 - 4}" font-size="11" fill="{MUTED}">{unit}</text>')
    s.append("</svg>")
    return "".join(s)


def score_chart(rows):
    """Horizontal bars, baselines and models side by side, worst at the bottom."""
    rows = [r for r in rows if r["mape"] is not None and r["mape"] == r["mape"]]
    W = 940
    row_h = 34
    H = 28 + row_h * len(rows) + 18
    x0, x1 = 232, W - 66
    hi = max(r["mape"] for r in rows) * 1.12

    s = [_open(W, H, "Forecast error by approach")]
    for i, r in enumerate(rows):
        y = 24 + i * row_h
        w = (x1 - x0) * r["mape"] / hi
        fill = DEEP if r["kind"] == "baseline" else ROSE
        op = "0.5" if r["kind"] == "baseline" else "0.92"
        s.append(f'<text x="{x0 - 12}" y="{y + 15}" text-anchor="end" font-size="13" '
                 f'fill="{INK}">{_esc(r["approach"])}</text>')
        s.append(f'<rect x="{x0}" y="{y + 3}" width="{w:.1f}" height="19" fill="{fill}" '
                 f'opacity="{op}" rx="2"/>')
        s.append(f'<text x="{x0 + w + 8:.1f}" y="{y + 17}" font-size="12.5" fill="{INK}" '
                 f'style="font-variant-numeric:tabular-nums">{r["mape"]:.2f}%</text>')
    s.append(f'<g transform="translate({x0},{H - 4})" font-size="12">')
    s.append(f'<rect x="0" y="-12" width="14" height="10" fill="{DEEP}" opacity="0.5"/>')
    s.append(f'<text x="20" y="-3" fill="{MUTED}">baseline</text>')
    s.append(f'<rect x="88" y="-12" width="14" height="10" fill="{ROSE}" opacity="0.92"/>')
    s.append(f'<text x="108" y="-3" fill="{MUTED}">model</text>')
    s.append("</g></svg>")
    return "".join(s)
