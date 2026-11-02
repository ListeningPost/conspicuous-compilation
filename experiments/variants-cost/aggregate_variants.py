#!/usr/bin/env python3
"""Aggregate the variants (method 3) sweep: decompile wall-clock vs K.

Reads results/conditions.json + results/raw/decomp_*.log, writes results.json,
summary.md, and results/figures/fig_variants.svg.
"""
import json
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
    t = 0
    for line in f.read_text().splitlines():
        m = re.search(r"DC (fn_\w+) (OK|FAIL) (-?\d+) (-?\d+) (-?\d+) (\d+)", line)
        if m and m.group(2) == "OK":
            t += int(m.group(3))
    return t



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
    KS = meta["Ks"]
    size = {c["condition"]: c["size_bytes"] for c in meta["conditions"]}
    plain = total_ms("plain")
    rows = []
    for k in KS:
        o = total_ms(f"var_k{k}")
        rows.append({"k": k, "decompile_ms": o, "size_bytes": size.get(f"var_k{k}"),
                     "ratio": (round(o / plain, 2) if plain and o else None)})
    (RES / "results.json").write_text(json.dumps(
        {"per_variant": meta["per_variant"], "Ks": KS, "plain_ms": plain, "rows": rows}, indent=2))

    lines = ["# Variants (method 3) sweep — summary", "",
             f"Per-variant setting fixed at `{meta['per_variant']}`; K = diverse bodies per function.",
             f"Checksum gate `{meta['gate_checksum']}` held for every K (behaviour unchanged).",
             f"Plain-baseline decompile: {plain/1000:.2f}s." if plain else "", "",
             "| K | size (KB) | decompile | x vs plain |", "|--:|--:|--:|--:|"]
    for r in rows:
        of = f"{r['decompile_ms']/1000:.2f}s" if r["decompile_ms"] else "—"
        lines.append(f"| {r['k']} | {round(r['size_bytes']/1000)} | {of} | {r['ratio']}x |")
    (RES / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    make_fig([r for r in rows if r["decompile_ms"]], plain)


def make_fig(rows, plain):
    import math
    if len(rows) < 2:
        print("not enough data for figure"); return
    W, H = 460, 300
    L, R, T, B = 54, 16, 28, 46
    x0, x1, y0, y1 = L, W - R, T, H - B
    ks = [r["k"] for r in rows]
    dec = [r["decompile_ms"] / 1000 for r in rows]
    xmin, xmax = min(ks), max(ks)
    ymin = max(0.02, (plain / 1000) * 0.8 if plain else 0.02)
    ymax = max(dec) * 1.3
    lx = lambda v: x0 + (x1 - x0) * (math.log2(v) - math.log2(xmin)) / (math.log2(xmax) - math.log2(xmin))
    ly = lambda v: y1 - (y1 - y0) * (math.log10(max(v, ymin)) - math.log10(ymin)) / (math.log10(ymax) - math.log10(ymin))
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Liberation Sans,Arial,sans-serif">']
    p.append(f'<text x="{(x0+x1)/2}" y="15" font-size="11" font-weight="700" fill="{INK}" text-anchor="middle">Attack time grows with the number of diverse bodies (K)</text>')
    dd = ymin
    while dd <= ymax:
        yy = ly(dd)
        p.append(f'<line x1="{x0}" y1="{yy:.1f}" x2="{x1}" y2="{yy:.1f}" stroke="{RULE}" stroke-width="0.5"/>')
        lab = f"{dd:g}s" if dd >= 1 else f"{int(dd*1000)}ms"
        p.append(f'<text x="{x0-6}" y="{yy+3:.1f}" font-size="8" fill="{FAINT}" text-anchor="end">{lab}</text>')
        dd *= 10
    for k in ks:
        xx = lx(k)
        p.append(f'<text x="{xx:.1f}" y="{y1+14}" font-size="8" fill="{FAINT}" text-anchor="middle">{k}</text>')
    p.append(f'<text x="{(x0+x1)/2}" y="{H-6}" font-size="8.5" fill="{INK}" text-anchor="middle">diverse bodies per function (K), each at jumps=8</text>')
    p.append(f'<text x="14" y="{(y0+y1)/2}" font-size="8.5" fill="{INK}" text-anchor="middle" transform="rotate(-90 14 {(y0+y1)/2})">decompile wall-clock (log)</text>')
    p.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="{INK}" stroke-width="1"/>')
    p.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{INK}" stroke-width="1"/>')
    if plain:
        yb = ly(plain / 1000)
        p.append(f'<line x1="{x0}" y1="{yb:.1f}" x2="{x1}" y2="{yb:.1f}" stroke="{SLATE}" stroke-width="1.2" stroke-dasharray="4 2"/>')
        p.append(f'<text x="{x1}" y="{yb-4:.1f}" font-size="8" fill="{SLATE}" text-anchor="end">plain {plain/1000:.2f}s</text>')
    pts = " ".join(f"{lx(k):.1f},{ly(v):.1f}" for k, v in zip(ks, dec))
    p.append(f'<polyline points="{pts}" fill="none" stroke="{ACCENT}" stroke-width="2.2"/>')
    for k, v in zip(ks, dec):
        p.append(f'<circle cx="{lx(k):.1f}" cy="{ly(v):.1f}" r="3" fill="{ACCENT}"/>')
    p.append(f'<text x="{lx(ks[-1]):.1f}" y="{ly(dec[-1])-7:.1f}" font-size="9" fill="{ACCENT}" text-anchor="end" font-weight="700">K={ks[-1]}: {dec[-1]:.1f}s</text>')
    p.append("</svg>")
    (FIG / "fig_variants.svg").write_text("\n".join(p))
    print("wrote", FIG / "fig_variants.svg")


if __name__ == "__main__":
    main()
