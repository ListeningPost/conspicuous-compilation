#!/usr/bin/env python3
"""Breadth dataset: decompile cost vs the NUMBER of obfuscated functions.

This is the alternative to experiments/decompile-cost (which sweeps the per-function
dial, i.e. depth). Here the per-function setting is held FIXED and we vary N, the
count of obfuscated functions, because that is how the countermeasure actually
deploys: a moderate setting applied broadly, not a pathological setting applied to
one function.

For each N we build two binaries of N distinct functions each:
  plain_n{N}   no obfuscation
  obf_n{N}     every function obfuscated at jumps=64, mba_depth=2 (the macro default band)
A per-build checksum gate (identical across plain/obf at each N) proves behaviour is
unchanged. Functions are made pairwise-distinct with per-index constants so the
compiler's identical-code-folding cannot merge them.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUST_OBF = REPO / "toolchain" / "rust-obf"
BUILD = HERE / "build"
RESULTS = HERE / "results"
SEED = "7"
NS = [1, 2, 4, 8, 16, 32, 48, 64]
SETTING = "jumps=64, mba_depth=2"


def func_src(k: int, obf: bool) -> str:
    # distinct per-index constants so identical-code-folding cannot merge functions
    c1 = (0x9E3779B97F4A7C15 ^ (k * 0x100000001B3)) & 0xFFFFFFFFFFFFFFFF
    c2 = (0xC2B2AE3D27D4EB4F + k * 2654435761) & 0xFFFFFFFFFFFFFFFF
    rot = (k % 61) + 1
    attr = f"#[llnv_obfuscate({SETTING})]" if obf else "#[inline(never)]"
    return f"""{attr}
#[no_mangle]
pub extern "C" fn fn_{k:03}(buf: &mut [u64; 8], n: u64) -> u64 {{
    let mut x = buf[{k % 8}] ^ n ^ {c1}u64;
    let mut i = 0u64;
    while i < 48 {{
        x = x.wrapping_mul({c2}u64 | 1).wrapping_add(i ^ {c1}u64);
        if (x & 1) == 0 {{ x = x.rotate_left({rot}); }} else {{ x ^= x >> 7; }}
        i += 1;
    }}
    buf[{k % 8}] = x;
    x
}}
"""


def build(n: int, obf: bool) -> dict:
    name = f"{'obf' if obf else 'plain'}_n{n}"
    crate = BUILD / name
    src = crate / "src"
    src.mkdir(parents=True, exist_ok=True)
    (crate / "Cargo.toml").write_text(f"""[package]
name = "b_{name}"
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
    funcs = "\n".join(func_src(k, obf) for k in range(n))
    names = [f"fn_{k:03}" for k in range(n)]
    calls = "\n".join(
        f"        cs = cs.rotate_left(1) ^ fn_{k:03}(black_box(&mut b), black_box(m));"
        for k in range(n))
    main = f"""#![allow(unused_imports, unused_parens, clippy::all)]
use llnv_rust_obf::llnv_obfuscate;
use std::hint::black_box;

{funcs}

fn seed_buf(s: u64) -> [u64; 8] {{
    let mut b = [0u64; 8]; let mut i = 0usize;
    while i < 8 {{ b[i] = s.wrapping_mul(i as u64 + 1).wrapping_add(0x1234 + i as u64); i += 1; }}
    b
}}
fn main() {{
    let mut cs = 0u64;
    for m in 0..64u64 {{
        let mut b = seed_buf(m ^ 0xabcdef);
{calls if calls else "        let _ = &mut b;"}
    }}
    println!("CHECKSUM={{}}", cs);
}}
"""
    (src / "main.rs").write_text(main)
    env = dict(os.environ, LLNV_SEED=SEED)
    subprocess.run(["cargo", "build", "--release", "--quiet"], cwd=crate, env=env, check=True)
    binpath = crate / "target" / "release" / "corpus"
    checksum = subprocess.run([str(binpath)], capture_output=True, text=True, check=True).stdout.strip()
    out = RESULTS / "bin" / f"corpus_{name}"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binpath, out)
    return {"condition": name, "n": n, "obf": obf, "setting": SETTING if obf else None,
            "binary": str(out), "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
            "size_bytes": out.stat().st_size, "checksum": checksum, "functions": names}


def main():
    RESULTS.mkdir(exist_ok=True)
    recs = []
    gate = {}
    for n in NS:
        for obf in (False, True):
            r = build(n, obf)
            # gate: plain and obf at the same N must agree
            key = n
            if key not in gate:
                gate[key] = r["checksum"]
            r["checksum_ok"] = (r["checksum"] == gate[key])
            flag = "OK" if r["checksum_ok"] else "!! MISMATCH"
            print(f"[build] {r['condition']:10} {flag} cs={r['checksum']} size={r['size_bytes']}")
            recs.append(r)
    (RESULTS / "conditions.json").write_text(json.dumps(
        {"seed": SEED, "setting": SETTING, "Ns": NS, "gate_by_n": gate, "conditions": recs}, indent=2))
    bad = [r["condition"] for r in recs if not r["checksum_ok"]]
    if bad:
        print("FATAL gate mismatch:", bad, file=sys.stderr); sys.exit(1)
    print(f"\nAll {len(recs)} binaries built; per-N checksum gate held.")


if __name__ == "__main__":
    main()
