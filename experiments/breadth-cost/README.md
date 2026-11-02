# Breadth dataset (alternative to the depth sweep)

This is a **second, alternative dataset**, kept on the `dataset/breadth` branch. It
tests the dimension that matches how the countermeasure actually deploys:
**breadth** — a fixed, moderate per-function setting applied to a growing *number*
of functions — rather than **depth** (one function, dial turned up), which is what
`experiments/decompile-cost` on `feature/will` sweeps.

The motivation is concrete: cranking the dial on a single function is the wrong
model. The compiler's memory and the decompiler's time both scale with surviving
basic blocks, so a single monster function breaks your own build (rustc OOMs around
a few thousand bogus states) long before it helps. The realistic knob is the number
of protected functions, each at a sane depth.

## Design

Per-function setting is fixed at `jumps=64, mba_depth=2`. For each
`N ∈ {1,2,4,8,16,32,48,64}` we build two binaries of N distinct functions:

| condition | meaning |
|---|---|
| `plain_n{N}` | N functions, no obfuscation |
| `obf_n{N}` | N functions, each obfuscated at the fixed setting |

Functions are made pairwise-distinct with per-index constants so the compiler's
identical-code-folding cannot merge them. A per-N checksum gate (plain and obf
agree at each N) proves behaviour is unchanged. Seed pinned to `LLNV_SEED=7`.

## Reproduce

```sh
cd experiments/breadth-cost
python3 gen_breadth.py        # build every condition; enforces the per-N gate
./run_breadth.sh              # Ghidra decompiles each function K times
python3 aggregate_breadth.py  # -> results/results.json, summary.md, figures/fig_breadth.svg
```

## Reading it

The claim is that total attacker decompile time grows **linearly with N** at a fixed
per-function cost, while the defender's size/runtime cost also grows linearly but
from a tiny slope. It is the honest "deploy broadly" companion to the depth
dose-response: you buy attacker time by protecting more functions, and every
function still compiles. Same threat model as the depth experiment: a static,
automated decompiler; a debugger still walks the one real path.
