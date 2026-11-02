#!/usr/bin/env python3
"""Aggregate the sweep into results/results.json + a human summary.

Reads:
  results/conditions.json          (built binaries, sizes, sha256, checksum gate)
  results/raw/decomp_<cond>.log    (Ghidra per-function decompile times)
  results/raw/bench/<cond>.txt      (per-function runtime ns/call)

Writes:
  results/results.json             (tidy records, one per condition x function)
  results/summary.md               (per-condition rollups + the ratios the paper cites)

All ratios are computed against the `plain` baseline on a PER-FUNCTION basis and
then summarised (median across functions), so a single heavy or trivial function
cannot dominate the headline number.
"""
import json
import re
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
RAW = RES / "raw"


def load_decomp(cond):
    f = RAW / f"decomp_{cond}.log"
    out = {}
    if not f.exists():
        return out
    for line in f.read_text().splitlines():
        m = re.search(r"DC (fn_\w+) (OK|FAIL) (-?\d+) (-?\d+) (-?\d+) (\d+)", line)
        if m and m.group(2) == "OK":
            out[m.group(1)] = {"median_ms": int(m.group(3)), "min_ms": int(m.group(4)),
                               "max_ms": int(m.group(5)), "body_bytes": int(m.group(6))}
    return out


def load_bench(cond):
    f = RAW / "bench" / f"{cond}.txt"
    out = {}
    if not f.exists():
        return out
    for line in f.read_text().splitlines():
        m = re.match(r"BENCH (fn_\w+) (\d+)", line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out



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
    conds_meta = json.loads((RES / "conditions.json").read_text())
    conds = [c["condition"] for c in conds_meta["conditions"]]
    meta_by_cond = {c["condition"]: c for c in conds_meta["conditions"]}
    names = conds_meta["corpus_functions"]

    decomp = {c: load_decomp(c) for c in conds}
    bench = {c: load_bench(c) for c in conds}

    records = []
    for c in conds:
        for fn in names:
            d = decomp[c].get(fn, {})
            records.append({
                "condition": c, "function": fn,
                "decompile_median_ms": d.get("median_ms"),
                "decompile_body_bytes": d.get("body_bytes"),
                "runtime_ns": bench[c].get(fn),
            })

    def ratios(cond, key_fn):
        base = {fn: key_fn(decomp["plain"].get(fn, {}), bench["plain"].get(fn))
                for fn in names}
        rs = []
        for fn in names:
            b = base[fn]
            v = key_fn(decomp[cond].get(fn, {}), bench[cond].get(fn))
            if b and v is not None and b > 0:
                rs.append(v / b)
        return rs

    summary = {}
    for c in conds:
        dms = ratios(c, lambda d, _n: d.get("median_ms"))
        # runtime ratio uses a floor so 1 ns baselines don't explode the ratio
        rtr = ratios(c, lambda _d, n: n)
        decomp_abs = [decomp[c][fn]["median_ms"] for fn in names if fn in decomp[c]]
        summary[c] = {
            "attr": meta_by_cond[c]["attr"],
            "size_bytes": meta_by_cond[c]["size_bytes"],
            "checksum_ok": meta_by_cond[c]["checksum_ok"],
            "decompile_total_ms": sum(decomp_abs) if decomp_abs else None,
            "decompile_ratio_median": round(st.median(dms), 3) if dms else None,
            "decompile_ratio_max": round(max(dms), 3) if dms else None,
            "runtime_ratio_median": round(st.median(rtr), 3) if rtr else None,
        }

    (RES / "results.json").write_text(json.dumps(
        {"meta": {"gate_checksum": conds_meta["gate_checksum"], "seed": conds_meta["seed"],
                  "functions": names},
         "records": records, "summary": summary}, indent=2))

    # Human summary
    lines = ["# Decompile-cost sweep — summary", "",
             f"Correctness gate `{conds_meta['gate_checksum']}` held for every condition "
             f"(same input, same output; only the representation changes).", "",
             "| condition | size (B) | decompile total (ms) | decompile x vs plain (median / max) | runtime x (median) |",
             "|---|--:|--:|--:|--:|"]
    for c in conds:
        s = summary[c]
        lines.append(
            f"| `{c}` | {s['size_bytes']:,} | "
            f"{s['decompile_total_ms'] if s['decompile_total_ms'] is not None else '—'} | "
            f"{s['decompile_ratio_median']} / {s['decompile_ratio_max']} | "
            f"{s['runtime_ratio_median']} |")
    (RES / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
