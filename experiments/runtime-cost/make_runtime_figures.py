#!/usr/bin/env python3
"""Build the five runtime (defender-cost) figures from results/results.json.

  fig_m1.svg      method 1 alone: avg ns/call vs ordinal level
  fig_m2.svg      method 2 alone
  fig_m3.svg      method 3 alone
  fig_pairs.svg   the three pairwise combinations overlaid
  fig_all.svg     all seven configurations overlaid
X axis = ordinal level (1..5), not a complexity measure; y = average ns/call across the 16-function
corpus; dashed grey = plain baseline.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)
DATA = json.loads((RES / "results.json").read_text())
LEVELS = DATA["levels"]

INK, FAINT, RULE, SLATE = "#1c1f24", "#6b7480", "#c9ccd2", "#5b6671"
# fixed categorical colors per config (identity, not rank)
COLOR = {
    "m1": "#8C4E08", "m2": "#0E6B4F", "m3": "#2850a0",
    "m1m2": "#b07d2a", "m1m3": "#7a3a8c", "m2m3": "#0f8a86", "m1m2m3": "#b02a37",
}
LABEL = {"m1": "A flatten", "m2": "B harden", "m3": "C variants",
         "m1m2": "A+B", "m1m3": "A+C", "m2m3": "B+C", "m1m2m3": "A+B+C"}


import statistics as _st
_FNS = DATA["functions"]
_PLAIN_FN = next(r for r in DATA["records"] if r.get("config") == "plain")["per_fn_ns"]


def _med_added(rec):
    # Robust per-call overhead: median over functions of (obf_fn - plain_fn).
    # Avoids the raw-average pathology where one microsecond-scale function
    # (fn_sum_primes, 85% of the corpus total) and its run-to-run variance
    # swamp the real tens-of-ns method overhead.
    deltas = [rec["per_fn_ns"][f] - _PLAIN_FN[f] for f in _FNS]
    return _st.median(deltas)


def series(config):
    pts = [(r["level"], _med_added(r)) for r in DATA["records"]
           if r.get("config") == config and r.get("per_fn_ns")]
    return sorted(pts)


PLAIN = 0.0  # baseline: added ns/call vs plain is 0 by construction


def fig(path, configs, title, legend=True):
    # Reserve a right-hand gutter for the legend so it never overlaps the
    # plotted lines (which climb into the top-right). The plot area keeps the
    # same size whether or not a legend is drawn.
    legend_w = 104 if legend else 0
    W, H = 460 + legend_w, 300
    L, R, T, B = 56, 16, 30, 46
    x0, x1, y0, y1 = L, 460 - R, T, H - B
    allv = [PLAIN]
    for c in configs:
        allv += [v for _, v in series(c)]
    lo, hi = min(allv), max(allv)
    pad = max(2.0, (hi - lo) * 0.12)
    ymin, ymax = lo - pad, hi + pad
    X = lambda L_: x0 + (x1 - x0) * (L_ - LEVELS[0]) / (LEVELS[-1] - LEVELS[0])
    Y = lambda v: y1 - (y1 - y0) * (v - ymin) / (ymax - ymin)
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Liberation Sans,Arial,sans-serif">']
    p.append(f'<text x="{(x0+x1)/2}" y="16" font-size="11" font-weight="700" fill="{INK}" text-anchor="middle">{title}</text>')
    # y grid (5 ticks)
    for i in range(5):
        v = ymin + (ymax - ymin) * i / 4
        yy = Y(v)
        p.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" stroke="{RULE}" stroke-width="0.5"/>')
        p.append(f'<text x="{x0-6}" y="{yy+3:.1f}" font-size="8" fill="{FAINT}" text-anchor="end">{v:.0f}</text>')
    for L_ in LEVELS:
        p.append(f'<text x="{X(L_):.1f}" y="{y1+14}" font-size="8" fill="{FAINT}" text-anchor="middle">{L_}</text>')
    p.append(f'<text x="{(x0+x1)/2}" y="{H-6}" font-size="8.5" fill="{INK}" text-anchor="middle">ordinal level (1&#8211;5), not a complexity measure</text>')
    p.append(f'<text x="14" y="{(y0+y1)/2}" font-size="8.5" fill="{INK}" text-anchor="middle" transform="rotate(-90 14 {(y0+y1)/2})">added ns/call vs plain (median)</text>')
    p.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="{INK}" stroke-width="1"/>')
    p.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{INK}" stroke-width="1"/>')
    # plain baseline (0 added)
    yb = Y(PLAIN)
    p.append(f'<line x1="{x0}" y1="{yb:.1f}" x2="{x1}" y2="{yb:.1f}" stroke="{SLATE}" stroke-width="1.2" stroke-dasharray="4 2"/>')
    p.append(f'<text x="{x0+4}" y="{yb-4:.1f}" font-size="7.5" fill="{SLATE}">plain (0)</text>')
    # series
    drawn = [c for c in configs if series(c)]
    # legend sits in the right gutter, vertically centered against the plot
    lgx = x1 + 22
    ly = (y0 + y1) / 2 - (len(drawn) * 13) / 2 + 6
    if legend and drawn:
        p.append(f'<text x="{lgx}" y="{ly-14:.1f}" font-size="7.6" font-weight="700" '
                 f'fill="{FAINT}" letter-spacing="0.5">CONFIGURATION</text>')
    for c in configs:
        s = series(c)
        if not s:
            continue
        col = COLOR[c]
        pts = " ".join(f"{X(L_):.1f},{Y(v):.1f}" for L_, v in s)
        p.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"/>')
        for L_, v in s:
            p.append(f'<circle cx="{X(L_):.1f}" cy="{Y(v):.1f}" r="2.6" fill="{col}"/>')
        if legend:
            p.append(f'<line x1="{lgx}" y1="{ly-2.5:.1f}" x2="{lgx+14}" y2="{ly-2.5:.1f}" stroke="{col}" stroke-width="2.2"/>')
            p.append(f'<circle cx="{lgx+7}" cy="{ly-2.5:.1f}" r="2.4" fill="{col}"/>')
            p.append(f'<text x="{lgx+20}" y="{ly:.1f}" font-size="8" fill="{INK}">{LABEL[c]}</text>')
            ly += 13
        else:
            lx, lv = s[-1]
            p.append(f'<text x="{X(lx):.1f}" y="{Y(lv)-5:.1f}" font-size="8" fill="{col}" text-anchor="end" font-weight="700">{LABEL[c]}</text>')
    p.append("</svg>")
    (FIG / path).write_text("\n".join(p))
    print("wrote", FIG / path)


fig("fig_m1.svg", ["m1"], "Method A alone (flatten): runtime vs level", legend=False)
fig("fig_m2.svg", ["m2"], "Method B alone (harden): runtime vs level", legend=False)
fig("fig_m3.svg", ["m3"], "Method C alone (variants): runtime vs level", legend=False)
fig("fig_pairs.svg", ["m1m2", "m1m3", "m2m3"], "Pairwise combinations: runtime vs level", legend=True)
fig("fig_all.svg", ["m1", "m2", "m3", "m1m2", "m1m3", "m2m3", "m1m2m3"],
    "All methods and combinations: runtime vs level", legend=True)
