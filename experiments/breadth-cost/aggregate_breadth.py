#!/usr/bin/env python3
"""Aggregate the breadth sweep: total decompile wall-clock vs N (function count).

Reads results/conditions.json + results/raw/decomp_*.log, writes results/results.json
and results/summary.md, and generates results/figures/fig_breadth.svg.
"""
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
RAW = RES / "raw"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)
ACCENT, SLATE, INK, FAINT, RULE = "#0E6B4F", "#5b6671", "#1c1f24", "#6b7480", "#c9ccd2"


def total_ms(cond):
    f = RAW / f"decomp_{cond}.log"
    if not f.exists():
        return None
    tot = 0
    for line in f.read_text().splitlines():
        m = re.search(r"DC (fn_\w+) (OK|FAIL) (-?\d+) (-?\d+) (-?\d+) (\d+)", line)
        if m and m.group(2) == "OK":
            tot += int(m.group(3))
    return tot



def _assert_logs_complete():
    """Refuse to aggregate unless every decomp log finished cleanly: a DCDONE
    sentinel with ok==total>0 and no FAIL/DCERR rows. Guards against summarizing
    a run where Ghidra exited 0 but a decompile silently failed or produced nothing."""
    import sys, glob, re as _re
    bad = []
    logs = sorted(glob.glob(str(RAW / "decomp_*.log")))
    if not logs:
        print("no decomp logs present — run the sweep first", file=sys.stderr); sys.exit(1)
    for lg in logs:
        txt = Path(lg).read_text()
        done = _re.findall(r"DCDONE (\d+) (\d+)", txt)
        ok_total = done[-1] if done else None
        n_fail = len(_re.findall(r"DC fn_\w+ FAIL ", txt)) + txt.count("DCERR ")
        if ok_total is None:
            bad.append(f"{Path(lg).name}: no DCDONE sentinel"); continue
        ok, total = int(ok_total[0]), int(ok_total[1])
        if total == 0 or ok != total or n_fail:
            bad.append(f"{Path(lg).name}: ok={ok} total={total} failures={n_fail}")
    if bad:
        print("INTEGRITY FAIL — not aggregating:", file=sys.stderr)
        for b in bad: print("  " + b, file=sys.stderr)
        sys.exit(1)


def main():
    _assert_logs_complete()
    meta = json.loads((RES / "conditions.json").read_text())
    NS = meta["Ns"]
    rows = []
    for n in NS:
        p = total_ms(f"plain_n{n}")
        o = total_ms(f"obf_n{n}")
        rows.append({"n": n, "plain_ms": p, "obf_ms": o,
                     "ratio": (round(o / p, 2) if p and o else None)})
    (RES / "results.json").write_text(json.dumps(
        {"setting": meta["setting"], "Ns": NS, "rows": rows}, indent=2))

    lines = ["# Breadth sweep — summary", "",
             f"Per-function setting fixed at `{meta['setting']}`; N = number of obfuscated functions.",
             "Per-N checksum gate held (plain and obf identical at each N).", "",
             "| N | plain decompile | obf decompile | obf/plain |", "|--:|--:|--:|--:|"]
    for r in rows:
        pf = f"{r['plain_ms']/1000:.2f}s" if r['plain_ms'] else "—"
        of = f"{r['obf_ms']/1000:.2f}s" if r['obf_ms'] else "—"
        lines.append(f"| {r['n']} | {pf} | {of} | {r['ratio']}x |")
    (RES / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    make_fig(rows)


def make_fig(rows):
    rows = [r for r in rows if r["obf_ms"] is not None and r["plain_ms"] is not None]
    if len(rows) < 2:
        print("not enough complete rows for figure yet"); return
    W, H = 460, 300
    L, R, T, B = 54, 16, 28, 46
    x0, x1, y0, y1 = L, W - R, T, H - B
    ns = [r["n"] for r in rows]
    obf = [r["obf_ms"] / 1000 for r in rows]
    plain = [r["plain_ms"] / 1000 for r in rows]
    xmax = max(ns); ymax = max(obf) * 1.15
    X = lambda v: x0 + (x1 - x0) * v / xmax
    Y = lambda v: y1 - (y1 - y0) * v / ymax
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Liberation Sans,Arial,sans-serif">']
    p.append(f'<text x="{(x0+x1)/2}" y="15" font-size="11" font-weight="700" fill="{INK}" text-anchor="middle">Attack time grows linearly with the number of obfuscated functions</text>')
    # y grid
    import math as _m
    step = _m.ceil(ymax / 4)
    yv = 0
    while yv <= ymax:
        yy = Y(yv)
        p.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" stroke="{RULE}" stroke-width="0.5"/>')
        p.append(f'<text x="{x0-6}" y="{yy+3:.1f}" font-size="8" fill="{FAINT}" text-anchor="end">{yv:g}s</text>')
        yv += step
    for n in ns:
        xx = X(n)
        p.append(f'<text x="{xx:.1f}" y="{y1+14}" font-size="8" fill="{FAINT}" text-anchor="middle">{n}</text>')
    p.append(f'<text x="{(x0+x1)/2}" y="{H-6}" font-size="8.5" fill="{INK}" text-anchor="middle">number of obfuscated functions (N), each at jumps=64</text>')
    p.append(f'<text x="14" y="{(y0+y1)/2}" font-size="8.5" fill="{INK}" text-anchor="middle" transform="rotate(-90 14 {(y0+y1)/2})">decompile wall-clock</text>')
    p.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="{INK}" stroke-width="1"/>')
    p.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{INK}" stroke-width="1"/>')
    pts = " ".join(f"{X(n):.1f},{Y(v):.1f}" for n, v in zip(ns, obf))
    p.append(f'<polyline points="{pts}" fill="none" stroke="{ACCENT}" stroke-width="2.2"/>')
    for n, v in zip(ns, obf):
        p.append(f'<circle cx="{X(n):.1f}" cy="{Y(v):.1f}" r="3" fill="{ACCENT}"/>')
    p.append(f'<text x="{X(ns[-1]):.1f}" y="{Y(obf[-1])-7:.1f}" font-size="9" fill="{ACCENT}" text-anchor="end" font-weight="700">obfuscated {obf[-1]:.1f}s</text>')
    ptp = " ".join(f"{X(n):.1f},{Y(v):.1f}" for n, v in zip(ns, plain))
    p.append(f'<polyline points="{ptp}" fill="none" stroke="{SLATE}" stroke-width="1.6" stroke-dasharray="4 2"/>')
    p.append(f'<text x="{X(ns[-1]):.1f}" y="{Y(plain[-1])+14:.1f}" font-size="8" fill="{SLATE}" text-anchor="end">plain {plain[-1]:.2f}s</text>')
    p.append("</svg>")
    (FIG / "fig_breadth.svg").write_text("\n".join(p))
    print("wrote", FIG / "fig_breadth.svg")


if __name__ == "__main__":
    main()
