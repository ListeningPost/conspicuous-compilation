# Decompile-cost experiment (Rust)

This experiment measures what the LLNV `#[llnv_obfuscate]` transformation costs an
**automated static attacker** (decompiler wall-clock time) and what it costs the
**defender** (runtime ns/call), across a population of functions and a sweep of
the obfuscation dial. It is the controlled, reproducible core evidence for the
"conspicuous compilation" paper.

It is deliberately **Rust-only**. Rust's optimizer keeps our annotated functions
as standalone symbols, so every condition compares the *same function* plain vs
obfuscated — an apples-to-apples decompile-time measurement with no inlining confound.

## What is measured

Two methods, measured alone and together:

- **Method 1 — control-flow flattening + bogus-state CFG inflation.** The body
  becomes a `loop { match state }` dispatcher surrounded by `jumps` unreachable
  bogus states. Toggle: `flatten=1`.
- **Method 2 — opaque-predicate routing + MBA-masked state constants.** State
  transitions pass through an always-true predicate `(7a²−1 ≠ b²)` and the state
  constants are XOR-masked with always-zero mixed-boolean-arithmetic terms, both
  barriered by `black_box` so neither the compiler nor the decompiler can fold
  them. Toggle: `harden=1`.

The thesis the experiment tests: **method 2 is what makes method 1 survive.**
Flattening alone emits bogus edges the optimizer proves dead and deletes;
hardening removes that proof, so the dead edges persist and the decompiler must
process them. The prediction is that `m1_*` ≈ `plain` while `both_*` grows with
the `jumps` dial.

## Conditions

| condition | attribute | meaning |
|---|---|---|
| `plain` | `#[inline(never)]` | baseline, no obfuscation |
| `m1_j{J}` | `flatten=1, harden=0, jumps=J` | method 1 only (prunable) |
| `m2_d2` | `flatten=0, harden=1, mba_depth=2` | method 2 only |
| `both_j{J}_d2` | `flatten=1, harden=1, jumps=J, mba_depth=2` | both; dose-response over J |
| `both_j256_d4` | `jumps=256, mba_depth=4` | heaviest tested (ceiling: j<=4096, d<=16) |

`J ∈ {8, 16, 32, 64, 128, 256}`. Seed pinned to `LLNV_SEED=7` for byte-reproducible builds.

## Reproduce

Prerequisites: a Rust toolchain, Python 3, and Ghidra 12.1.4 headless at
`/opt/ghidra_12.1.4_PUBLIC` (edit the path in `run_sweep.sh` if yours differs).
Exact versions used are in `env.lock`.

```sh
cd experiments/decompile-cost
python3 gen_build.py        # build every condition; aborts if the checksum gate ever differs
./run_sweep.sh              # Ghidra decompiles each corpus function K times per condition
python3 aggregate.py        # -> results/results.json and results/summary.md
```

Runtime overhead is captured by the same binaries:

```sh
for b in results/bin/corpus_*; do echo "$b"; "$b" bench; done
```

## Layout

```
corpus.rs.in       the function corpus; one /*ATTR*/ marker per function
gen_build.py       rewrites /*ATTR*/ per condition, builds, enforces the checksum gate
run_sweep.sh       drives Ghidra headless over every built binary
harness/
  DecompCorpus.java  decompiles each fn_* K times, reports per-function median ms
aggregate.py       tidies raw logs into results.json + summary.md
results/
  conditions.json  built binaries, sizes, sha256, checksum
  bin/             the exact analyzed binaries (archived for provenance)
  raw/             Ghidra logs and per-function bench output
  results.json     tidy records + per-condition rollups
  summary.md       the table the paper cites
env.lock           tool versions, CPU, seed, repo commit
```

## Reading the results honestly

- The **correctness gate** (`CHECKSUM`) is identical in every condition. Same work
  in, same answer out; only the recovered representation changes.
- Decompile-time ratios are computed **per function** against that function's own
  plain baseline, then summarised with the **median across functions**, so one
  heavy or trivial function cannot set the headline number.
- The attacker modelled here is a **static, automated decompiler** (Ghidra). A
  debugger that runs the binary observes the one real path directly and is not
  impeded; that is a limitation, not an oversight. See the paper's threat model.
- Runtime overhead is a near-**constant additive** cost (the entry predicate), not
  multiplicative, and does **not** grow with `jumps` because bogus states never
  execute. Expect large *ratios* on trivial functions and negligible *absolute*
  cost on functions doing real work.
