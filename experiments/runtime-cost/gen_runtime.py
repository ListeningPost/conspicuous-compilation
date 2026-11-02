#!/usr/bin/env python3
"""Runtime (defender-cost) study: average ns/call vs complexity, per method and
per method-combination.

The three methods have different knobs, so we put them on a common complexity
LEVEL axis (1..5); each level cranks the knobs that a configuration uses:
    level:        1    2    3    4    5
    jumps  (m1):  8    16   32   64   128
    mba_depth(m2):1    2    3    4    5
    variants(m3): 2    3    4    6    8

Seven configurations (each builds the same 16-function corpus and is benched):
    m1, m2, m3, m1m2, m1m3, m2m3, m1m2m3
plus a `plain` baseline. A checksum gate (identical to plain) holds for every
build. Note: m3 (and any config with variants) carries a minimal flatten+harden
per body, because distinct variants only survive the optimizer when hardened --
diversity depends on hardening the same way flattening does.

Builds are power-independent; the ns/call BENCH must run on AC with the governor
pinned to `performance`.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUST_OBF = REPO / "toolchain" / "rust-obf"
TEMPLATE = (HERE / "corpus.rs.in").read_text()
BUILD = HERE / "build"
RESULTS = HERE / "results"
SEED = "7"
LEVELS = [1, 2, 3, 4, 5]
JUMPS = {1: 8, 2: 16, 3: 32, 4: 64, 5: 128}
DEPTH = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
VARS = {1: 2, 2: 3, 3: 4, 4: 6, 5: 8}
NAMES = re.findall(r"pub extern \"C\" fn (fn_\w+)", TEMPLATE)

# config -> function(level) -> attr string (knobs it does NOT use stay at the floor)
def attr(config: str, L: int) -> str:
    j, d, v = JUMPS[L], DEPTH[L], VARS[L]
    cfg = {
        "m1":     f"flatten=1, harden=0, jumps={j}, mba_depth=1, variants=1",
        "m2":     f"flatten=0, harden=1, jumps=8, mba_depth={d}, variants=1",
        "m3":     f"flatten=1, harden=1, jumps=8, mba_depth=1, variants={v}",
        "m1m2":   f"flatten=1, harden=1, jumps={j}, mba_depth={d}, variants=1",
        "m1m3":   f"flatten=1, harden=0, jumps={j}, mba_depth=1, variants={v}",
        "m2m3":   f"flatten=0, harden=1, jumps=8, mba_depth={d}, variants={v}",
        "m1m2m3": f"flatten=1, harden=1, jumps={j}, mba_depth={d}, variants={v}",
    }[config]
    return f"#[llnv_obfuscate({cfg})]"


def main_tail() -> str:
    table = ",\n".join(f'        ("{n}", {n})' for n in NAMES)
    return f"""
type CorpusFn = extern "C" fn(&mut [u64; 8], u64) -> u64;
const TABLE: &[(&str, CorpusFn)] = &[
{table}
];
fn seed_buf(s: u64) -> [u64; 8] {{
    let mut b = [0u64; 8]; let mut i = 0usize;
    while i < 8 {{ b[i] = s.wrapping_mul(i as u64 + 1).wrapping_add(0x1234 + i as u64); i += 1; }}
    b
}}
fn checksum() -> u64 {{
    let mut cs = 0u64;
    for m in 0..64u64 {{ let mut b = seed_buf(m ^ 0xabcdef);
        for (_, f) in TABLE {{ cs = cs.rotate_left(1) ^ f(black_box(&mut b), black_box(m)); }} }}
    cs
}}
fn bench() {{
    use std::time::Instant;
    const REPS: usize = 11; const INNER: u64 = 20_000;
    for (name, f) in TABLE {{
        let mut s = [0u64; REPS];
        let mut b = seed_buf(0x55);
        for m in 0..2000u64 {{ black_box(f(black_box(&mut b), black_box(m))); }}
        for r in 0..REPS {{ let mut b = seed_buf(r as u64); let t0 = Instant::now(); let mut acc = 0u64;
            for m in 0..INNER {{ acc ^= f(black_box(&mut b), black_box(m)); }}
            s[r] = t0.elapsed().as_nanos() as u64 / INNER; black_box(acc); }}
        s.sort_unstable();
        println!("BENCH {{}} {{}}", name, s[REPS / 2]);
    }}
}}
fn main() {{ if std::env::args().any(|a| a == "bench") {{ bench(); }} else {{ println!("CHECKSUM={{}}", checksum()); }} }}
"""


def build_and_bench(cond: str, attr_str: str) -> dict:
    crate = BUILD / cond
    (crate / "src").mkdir(parents=True, exist_ok=True)
    (crate / "Cargo.toml").write_text(f"""[package]
name = "r_{cond}"
version = "0.0.0"
edition = "2021"
[dependencies]
llnv-rust-obf = {{ path = "{RUST_OBF.as_posix()}" }}
[[bin]]
name = "corpus"
path = "src/main.rs"
[profile.release]
opt-level = 3
lto = false
codegen-units = 16
""")
    body = TEMPLATE.replace("/*ATTR*/", attr_str) + main_tail()
    (crate / "src" / "main.rs").write_text(body)
    env = dict(os.environ, LLNV_SEED=SEED)
    subprocess.run(["cargo", "build", "--release", "--quiet"], cwd=crate, env=env, check=True, timeout=600)
    binp = crate / "target" / "release" / "corpus"
    checksum = subprocess.run([str(binp)], capture_output=True, text=True, check=True).stdout.strip()
    # bench
    out = subprocess.run([str(binp), "bench"], capture_output=True, text=True, check=True).stdout
    per_fn = {}
    for line in out.splitlines():
        m = re.match(r"BENCH (fn_\w+) (\d+)", line)
        if m:
            per_fn[m.group(1)] = int(m.group(2))
    avg = round(sum(per_fn.values()) / len(per_fn), 1) if per_fn else None
    # keep the binary small footprint: drop the heavy build tree after benching
    shutil.rmtree(crate / "target", ignore_errors=True)
    return {"condition": cond, "attr": attr_str, "checksum": checksum,
            "avg_ns": avg, "per_fn_ns": per_fn}


def main():
    RESULTS.mkdir(exist_ok=True)
    recs = []
    gate = None
    # plain baseline
    r = build_and_bench("plain", "#[inline(never)]")
    gate = r["checksum"]; r["checksum_ok"] = True; r["config"] = "plain"; r["level"] = 0
    print(f"[plain]             avg_ns={r['avg_ns']}")
    recs.append(r)
    for config in ["m1", "m2", "m3", "m1m2", "m1m3", "m2m3", "m1m2m3"]:
        for L in LEVELS:
            cond = f"{config}_L{L}"
            try:
                r = build_and_bench(cond, attr(config, L))
            except subprocess.TimeoutExpired:
                print(f"[{cond}] BUILD TIMEOUT (skipped)"); continue
            r["checksum_ok"] = (r["checksum"] == gate)
            r["config"] = config; r["level"] = L
            flag = "OK" if r["checksum_ok"] else "!! GATE MISMATCH"
            print(f"[{cond:12}] avg_ns={r['avg_ns']:<8} {flag}")
            recs.append(r)
    (RESULTS / "results.json").write_text(json.dumps(
        {"seed": SEED, "levels": LEVELS, "jumps": JUMPS, "depth": DEPTH, "variants": VARS,
         "gate_checksum": gate, "functions": NAMES, "records": recs}, indent=2))
    bad = [r["condition"] for r in recs if not r.get("checksum_ok")]
    if bad:
        print("WARNING gate mismatch:", bad, file=sys.stderr)
    print(f"\nDone: {len(recs)} binaries benched; gate {gate}.")


if __name__ == "__main__":
    main()
