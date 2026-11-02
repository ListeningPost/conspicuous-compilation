#!/usr/bin/env python3
"""Generate publication SVG figures from results/results.json.

Focused on the one quantity the paper is about: the attacker's wall-clock time to
decompile the corpus. Figures (written to results/figures/):
  fig_attacktime.svg  absolute Ghidra decompile wall-clock (seconds) vs the dial.
  fig_methods.svg     the same wall-clock, by method, at jumps=64.
Palette matches the paper: accent #0E6B4F, slate #5b6671, amber #8C4E08.
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)
S = json.loads((RES / "results.json").read_text())["summary"]

ACCENT, SLATE, AMBER, INK, FAINT, RULE = "#0E6B4F", "#5b6671", "#8C4E08", "#1c1f24", "#6b7480", "#c9ccd2"

JUMPS = [8, 16, 32, 64, 128, 256]
sec = lambda c: S[c]["decompile_total_ms"] / 1000.0
dec_s = [sec(f"both_j{j}_d2") for j in JUMPS]
plain_s = sec("plain")
ratio = {j: S[f"both_j{j}_d2"]["decompile_ratio_median"] for j in JUMPS}


def logmap(v, vmin, vmax, lo, hi):
    return lo + (hi - lo) * (math.log10(v) - math.log10(vmin)) / (math.log10(vmax) - math.log10(vmin))


def fig_attacktime():
    W, H = 460, 300
    L, R, T, B = 54, 18, 28, 46
    x0, x1, y0, y1 = L, W - R, T, H - B
    xmin, xmax = 8, 256
    ymin, ymax = 0.03, 30.0
    X = lambda j: logmap(j, xmin, xmax, x0, x1)
    Y = lambda v: logmap(max(v, ymin), ymin, ymax, y1, y0)
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Liberation Sans,Arial,sans-serif">']
    p.append(f'<text x="{(x0+x1)/2}" y="15" font-size="11" font-weight="700" fill="{INK}" text-anchor="middle">Wall-clock to decompile the corpus rises with the dial</text>')
    for d in (0.03, 0.1, 1, 10, 30):
        yy = Y(d)
        p.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" stroke="{RULE}" stroke-width="0.5"/>')
        lab = f"{d:g}s" if d >= 1 else f"{int(d*1000)}ms"
        p.append(f'<text x="{x0-6}" y="{yy+3:.1f}" font-size="8" fill="{FAINT}" text-anchor="end">{lab}</text>')
    for j in JUMPS:
        xx = X(j)
        p.append(f'<line x1="{xx:.1f}" y1="{y1}" x2="{xx:.1f}" y2="{y1+3}" stroke="{FAINT}" stroke-width="0.6"/>')
        p.append(f'<text x="{xx:.1f}" y="{y1+14}" font-size="8" fill="{FAINT}" text-anchor="middle">{j}</text>')
    p.append(f'<text x="{(x0+x1)/2}" y="{H-6}" font-size="8.5" fill="{INK}" text-anchor="middle">bogus-branch dial (jumps)</text>')
    p.append(f'<text x="14" y="{(y0+y1)/2}" font-size="8.5" fill="{INK}" text-anchor="middle" transform="rotate(-90 14 {(y0+y1)/2})">decompile wall-clock (log)</text>')
    p.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="{INK}" stroke-width="1"/>')
    p.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{INK}" stroke-width="1"/>')
    # plain baseline
    yb = Y(plain_s)
    p.append(f'<line x1="{x0}" y1="{yb:.1f}" x2="{x1}" y2="{yb:.1f}" stroke="{SLATE}" stroke-width="1.3" stroke-dasharray="4 2"/>')
    p.append(f'<text x="{x1}" y="{yb-4:.1f}" font-size="8" fill="{SLATE}" text-anchor="end">plain {plain_s*1000:.0f} ms</text>')
    # both curve
    pts = " ".join(f"{X(j):.1f},{Y(v):.1f}" for j, v in zip(JUMPS, dec_s))
    p.append(f'<polyline points="{pts}" fill="none" stroke="{ACCENT}" stroke-width="2.2"/>')
    for j, v in zip(JUMPS, dec_s):
        p.append(f'<circle cx="{X(j):.1f}" cy="{Y(v):.1f}" r="3" fill="{ACCENT}"/>')
    p.append(f'<text x="{X(256):.1f}" y="{Y(dec_s[-1])-7:.1f}" font-size="9" fill="{ACCENT}" text-anchor="end" font-weight="700">{dec_s[-1]:.0f} s &#160;({ratio[256]:.0f}&#215;)</text>')
    p.append(f'<text x="{X(8)+8:.1f}" y="{Y(dec_s[0])+13:.1f}" font-size="8" fill="{ACCENT}" font-weight="700">methods A+B</text>')
    p.append("</svg>")
    (FIG / "fig_attacktime.svg").write_text("\n".join(p))


def fig_methods():
    W, H = 360, 250
    L, R, T, Bm = 50, 14, 40, 52
    x0, x1, y0, y1 = L, W - R, T, H - Bm
    conds = [("plain", "plain", SLATE), ("m1_j64", "A\n(flatten)", AMBER),
             ("m2_d2", "B\n(harden)", AMBER), ("both_j64_d2", "A+B", ACCENT)]
    vals = [sec(c) for c, _, _ in conds]       # seconds
    rats = [S[c]["decompile_ratio_median"] for c, _, _ in conds]
    ymin, ymax = 0.03, 10.0
    Y = lambda v: y1 - (y1 - y0) * (math.log10(max(v, ymin)) - math.log10(ymin)) / (math.log10(ymax) - math.log10(ymin))
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Liberation Sans,Arial,sans-serif">']
    p.append(f'<text x="{(x0+x1)/2}" y="14" font-size="11" font-weight="700" fill="{INK}" text-anchor="middle">Only the two methods together cost real time</text>')
    p.append(f'<text x="{(x0+x1)/2}" y="27" font-size="8.5" fill="{FAINT}" text-anchor="middle">decompile wall-clock at jumps=64</text>')
    for d in (0.03, 0.1, 1, 10):
        yy = Y(d)
        p.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" stroke="{RULE}" stroke-width="0.5"/>')
        lab = f"{d:g}s" if d >= 1 else f"{int(d*1000)}ms"
        p.append(f'<text x="{x0-5}" y="{yy+3:.1f}" font-size="8" fill="{FAINT}" text-anchor="end">{lab}</text>')
    n = len(conds); bw = (x1 - x0) / n * 0.56
    for i, ((c, lab, col), v, rr) in enumerate(zip(conds, vals, rats)):
        cx = x0 + (x1 - x0) * (i + 0.5) / n
        yy = Y(v)
        p.append(f'<rect x="{cx-bw/2:.1f}" y="{yy:.1f}" width="{bw:.1f}" height="{y1-yy:.1f}" fill="{col}" rx="2"/>')
        tlab = f"{v:.2f}s" if v >= 1 else f"{v*1000:.0f}ms"
        p.append(f'<text x="{cx:.1f}" y="{yy-4:.1f}" font-size="8.5" fill="{INK}" text-anchor="middle" font-weight="700">{tlab}</text>')
        for k, ln in enumerate(lab.split("\n")):
            p.append(f'<text x="{cx:.1f}" y="{y1+14+k*10:.1f}" font-size="8" fill="{FAINT}" text-anchor="middle">{ln}</text>')
    p.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{INK}" stroke-width="1"/>')
    p.append("</svg>")
    (FIG / "fig_methods.svg").write_text("\n".join(p))


fig_attacktime()
fig_methods()
print("wrote fig_attacktime.svg, fig_methods.svg")
print("both seconds:", dict(zip(JUMPS, [round(x, 3) for x in dec_s])), "plain", plain_s)
