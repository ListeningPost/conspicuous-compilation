#!/usr/bin/env python3
"""Generate and build one Rust binary per experimental condition.

Each condition rewrites the `/*ATTR*/` marker in corpus.rs.in with a different
per-function attribute, appends a fixed `main` (the checksum correctness gate),
compiles with a pinned LLNV_SEED, verifies the checksum is identical across all
conditions, and records the binary path + sha256 in results/conditions.json.

Conditions (Rust only):
  plain            no obfuscation (baseline)
  m1_j{J}          method 1 only: flatten + bogus CFG, NO hardening (prunable)
  m2_d{D}          method 2 only: opaque predicate + MBA, NO bogus inflation
  both_j{J}_d{D}   both methods combined
The `both_*` row is also swept over J for the dose-response curve.
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
BUILD_ROOT = HERE / "build"
RESULTS = HERE / "results"
SEED = "7"

NAMES = re.findall(r"pub extern \"C\" fn (fn_\w+)", TEMPLATE)

# Fixed driver appended to every generated crate. Identical in every condition,
# so the printed checksum depends only on behaviour, never on obfuscation.
def main_tail() -> str:
    table = ",\n".join(f'        ("{name}", {name})' for name in NAMES)
    return f"""
type CorpusFn = extern "C" fn(&mut [u64; 8], u64) -> u64;

const TABLE: &[(&str, CorpusFn)] = &[
{table}
];

fn seed_buf(s: u64) -> [u64; 8] {{
    let mut b = [0u64; 8];
    let mut i = 0usize;
    while i < 8 {{ b[i] = s.wrapping_mul(i as u64 + 1).wrapping_add(0x1234 + i as u64); i += 1; }}
    b
}}

// Correctness gate: fold every function's output over a fixed input sweep.
fn checksum() -> u64 {{
    let mut cs = 0u64;
    for n in 0..64u64 {{
        let mut b = seed_buf(n ^ 0xabcdef);
        for (_, f) in TABLE {{
            cs = cs.rotate_left(1) ^ f(black_box(&mut b), black_box(n));
        }}
    }}
    cs
}}

// Runtime cost: median ns/call per function, interleaved reps to cancel drift.
fn bench() {{
    use std::time::Instant;
    const REPS: usize = 11;
    const INNER: u64 = 20_000;
    for (name, f) in TABLE {{
        let mut samples = [0u64; REPS];
        // warm
        let mut b = seed_buf(0x55);
        for n in 0..2000u64 {{ black_box(f(black_box(&mut b), black_box(n))); }}
        for r in 0..REPS {{
            let mut b = seed_buf(r as u64);
            let t0 = Instant::now();
            let mut acc = 0u64;
            for n in 0..INNER {{ acc ^= f(black_box(&mut b), black_box(n)); }}
            let ns = t0.elapsed().as_nanos() as u64 / INNER;
            black_box(acc);
            samples[r] = ns;
        }}
        samples.sort_unstable();
        println!("BENCH {{}} {{}}", name, samples[REPS / 2]);
    }}
}}

fn main() {{
    if std::env::args().any(|a| a == "bench") {{
        bench();
    }} else {{
        println!("CHECKSUM={{}}", checksum());
    }}
}}
"""


def attr_for(cond: str) -> str:
    if cond == "plain":
        return "#[inline(never)]"
    m = re.fullmatch(r"m1_j(\d+)", cond)
    if m:
        return f"#[llnv_obfuscate(flatten=1, harden=0, jumps={m.group(1)})]"
    m = re.fullmatch(r"m2_d(\d+)", cond)
    if m:
        return f"#[llnv_obfuscate(flatten=0, harden=1, mba_depth={m.group(1)})]"
    m = re.fullmatch(r"both_j(\d+)_d(\d+)", cond)
    if m:
        return (f"#[llnv_obfuscate(flatten=1, harden=1, "
                f"jumps={m.group(1)}, mba_depth={m.group(2)})]")
    raise ValueError(f"unknown condition {cond}")


def conditions() -> list[str]:
    conds = ["plain"]
    # three-method comparison at a fixed moderate level
    conds += ["m1_j64", "m2_d2", "both_j64_d2"]
    # dose-response: both, sweep jumps at fixed mba_depth
    for j in (8, 16, 32, 128, 256):
        conds.append(f"both_j{j}_d2")
    # heaviest setting we sweep (dial ceiling is far higher: jumps<=4096, mba_depth<=16)
    conds.append("both_j256_d4")
    # method-1 dose-response control (flatten only, same jumps sweep)
    for j in (8, 16, 32, 128, 256):
        conds.append(f"m1_j{j}")
    # dedupe, keep order
    seen, out = set(), []
    for c in conds:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def build(cond: str) -> dict:
    crate = BUILD_ROOT / cond
    src = crate / "src"
    src.mkdir(parents=True, exist_ok=True)
    (crate / "Cargo.toml").write_text(f"""[package]
name = "cond_{cond}"
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
    (src / "main.rs").write_text(body)
    env = dict(os.environ, LLNV_SEED=SEED)
    subprocess.run(["cargo", "build", "--release", "--quiet"],
                   cwd=crate, env=env, check=True)
    binpath = crate / "target" / "release" / "corpus"
    checksum = subprocess.run([str(binpath)], capture_output=True, text=True,
                              check=True).stdout.strip()
    out_bin = RESULTS / "bin" / f"corpus_{cond}"
    out_bin.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binpath, out_bin)
    sha = hashlib.sha256(out_bin.read_bytes()).hexdigest()
    size = out_bin.stat().st_size
    return {"condition": cond, "attr": attr_for(cond), "binary": str(out_bin),
            "sha256": sha, "size_bytes": size, "checksum": checksum}


def main():
    RESULTS.mkdir(exist_ok=True)
    recs = []
    gate = None
    for cond in conditions():
        print(f"[build] {cond} ...", flush=True)
        rec = build(cond)
        if gate is None:
            gate = rec["checksum"]
        ok = rec["checksum"] == gate
        rec["checksum_ok"] = ok
        flag = "OK" if ok else "!! CHECKSUM MISMATCH"
        print(f"        {flag}  {rec['checksum']}  size={rec['size_bytes']}  {rec['sha256'][:12]}")
        recs.append(rec)
    (RESULTS / "conditions.json").write_text(json.dumps(
        {"seed": SEED, "corpus_functions": NAMES, "gate_checksum": gate,
         "conditions": recs}, indent=2))
    bad = [r["condition"] for r in recs if not r["checksum_ok"]]
    if bad:
        print(f"\nFATAL: checksum gate failed for: {bad}", file=sys.stderr)
        sys.exit(1)
    print(f"\nAll {len(recs)} conditions built; checksum gate {gate} held for all.")


if __name__ == "__main__":
    main()
