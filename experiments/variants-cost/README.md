# Variants dataset — method 3 (runtime-selected diverse bodies)

Third dataset, on the `dataset/variants` branch. It re-creates the decompile-cost
experiment using the new `variants=K` feature of the Rust macro.

## The feature

`#[llnv_obfuscate(..., variants=K)]` emits **K independently-flattened,
independently-scrambled copies** of the function — each with its own entry, state
constants, shuffle and bogus padding — behind an outer dispatcher that hashes the
wall clock at call time (`SystemTime::now()`, via a MurmurHash3 finalizer) and
selects one. Each call runs a different jumbled body for the same observable
result, so which variant executes is not statically determined. Unlike approaches
that build N entry routes converging on **one** shared body, this builds N
**distinct** bodies.

## Design

The per-variant flattening is held FIXED and small (`jumps=8, mba_depth=1`) so that
even K=64 compiles comfortably, and we sweep **K** on the same 16-function corpus:

| condition | K | meaning |
|---|--:|---|
| `plain` | 0 | no obfuscation |
| `var_k{K}` | 1..64 | each function has K diverse bodies |

`K ∈ {1,2,4,8,16,32,64}`. `var_k1` is the single-body baseline (methods 1+2, no
diversity); larger K adds bodies. A per-condition checksum gate (identical to plain)
proves behaviour is unchanged regardless of which variant runs. Seed `LLNV_SEED=7`.

## Reproduce (run on AC power, governor = performance)

```sh
cd experiments/variants-cost
python3 gen_variants.py       # build every K; enforces the checksum gate
./run_variants.sh             # Ghidra decompiles each function K times
python3 aggregate_variants.py # -> results.json, summary.md, figures/fig_variants.svg
```

## Reading it, and the honest caveat

Decompile cost is expected to grow with K, because each of the K bodies is an
independent maze the static decompiler must recover (~K x the single-body volume).
But the *primary* purpose of variants is **runtime** diversity — defeating a
dynamic attacker doing trace-diffing or replay, since the executed path changes per
run. That benefit does NOT show up in a static decompile-time metric; it would need
a dynamic-analysis cost measurement. As with methods 1 and 2, a debugger still
observes whichever body actually runs. So this dataset measures the *static volume*
cost of diversity, not its anti-dynamic benefit, and says so.
