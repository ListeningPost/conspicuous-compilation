#!/usr/bin/env python3
"""Variants dataset (method 3): decompile cost vs K, the number of runtime-selected
diverse bodies per function.

This re-creates the decompile-cost experiment with the new `variants=K` feature:
the per-function flattening/hardening is held FIXED and small, and we sweep K, the
number of independently-flattened bodies the macro emits behind a wall-clock
time-hash selector. Each call runs one of the K bodies; which one is not statically
determined. This is the third approach: K distinct bodies, not shared-body entry
routes that converge on one implementation.

Conditions: plain, then var_k{1,2,4,8,16,32,64} at fixed jumps=8, mba_depth=1.
A per-condition checksum gate (identical to plain) proves behaviour is unchanged
regardless of which variant executes. Seed pinned LLNV_SEED=7.
"""
import hashlib
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
KS = [1, 2, 4, 8, 16, 32, 64]
PER_VARIANT = "flatten=1, harden=1, jumps=8, mba_depth=1"
NAMES = re.findall(r"pub extern \"C\" fn (fn_\w+)", TEMPLATE)


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
    for m in 0..64u64 {{
        let mut b = seed_buf(m ^ 0xabcdef);
        for (_, f) in TABLE {{ cs = cs.rotate_left(1) ^ f(black_box(&mut b), black_box(m)); }}
    }}
    cs
}}
fn bench() {{
    use std::time::Instant;
    const REPS: usize = 11; const INNER: u64 = 20_000;
    for (name, f) in TABLE {{
        let mut s = [0u64; REPS];
        let mut b = seed_buf(0x55);
        for m in 0..2000u64 {{ black_box(f(black_box(&mut b), black_box(m))); }}
        for r in 0..REPS {{
            let mut b = seed_buf(r as u64);
            let t0 = Instant::now();
            let mut acc = 0u64;
            for m in 0..INNER {{ acc ^= f(black_box(&mut b), black_box(m)); }}
            s[r] = t0.elapsed().as_nanos() as u64 / INNER;
            black_box(acc);
        }}
        s.sort_unstable();
        println!("BENCH {{}} {{}}", name, s[REPS / 2]);
    }}
}}
fn main() {{
    if std::env::args().any(|a| a == "bench") {{ bench(); }}
    else {{ println!("CHECKSUM={{}}", checksum()); }}
}}
"""


def attr_for(cond: str) -> str:
    if cond == "plain":
        return "#[inline(never)]"
    m = re.fullmatch(r"var_k(\d+)", cond)
    if m:
        return f"#[llnv_obfuscate({PER_VARIANT}, variants={m.group(1)})]"
    raise ValueError(cond)


def build(cond: str) -> dict:
    crate = BUILD / cond
    (crate / "src").mkdir(parents=True, exist_ok=True)
    (crate / "Cargo.toml").write_text(f"""[package]
name = "v_{cond}"
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
    body = TEMPLATE.replace("/*ATTR*/", attr_for(cond)) + main_tail()
    (crate / "src" / "main.rs").write_text(body)
    env = dict(os.environ, LLNV_SEED=SEED)
    subprocess.run(["cargo", "build", "--release", "--quiet"], cwd=crate, env=env, check=True)
    binp = crate / "target" / "release" / "corpus"
    checksum = subprocess.run([str(binp)], capture_output=True, text=True, check=True).stdout.strip()
    out = RESULTS / "bin" / f"corpus_{cond}"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binp, out)
    return {"condition": cond, "attr": attr_for(cond), "binary": str(out),
            "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "size_bytes": out.stat().st_size, "checksum": checksum}


def main():
    RESULTS.mkdir(exist_ok=True)
    conds = ["plain"] + [f"var_k{k}" for k in KS]
    recs, gate = [], None
    for c in conds:
        r = build(c)
        gate = gate or r["checksum"]
        r["checksum_ok"] = (r["checksum"] == gate)
        print(f"[build] {c:9} {'OK' if r['checksum_ok'] else '!! MISMATCH'} "
              f"{r['checksum']} size={r['size_bytes']}")
        recs.append(r)
    (RESULTS / "conditions.json").write_text(json.dumps(
        {"seed": SEED, "per_variant": PER_VARIANT, "Ks": KS, "corpus_functions": NAMES,
         "gate_checksum": gate, "conditions": recs}, indent=2))
    bad = [r["condition"] for r in recs if not r["checksum_ok"]]
    if bad:
        print("FATAL gate mismatch:", bad, file=sys.stderr); sys.exit(1)
    print(f"\nAll {len(recs)} built; checksum gate {gate} held.")


if __name__ == "__main__":
    main()
