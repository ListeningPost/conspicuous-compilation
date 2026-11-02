# Runtime (defender-cost) study

The decompile experiments measure the *attacker's* cost. This one measures the
*defender's*: the runtime added by each method and each combination, as a function
of complexity. It answers "what do we pay, per call, for each method?"

## Design

Seven configurations on the same 16-function corpus, swept over a shared
**complexity level** (1..5) so the three methods are comparable. Each level cranks
the knobs a configuration uses:

| level | jumps (M1) | mba_depth (M2) | variants (M3) |
|--:|--:|--:|--:|
| 1 | 8 | 1 | 2 |
| 2 | 16 | 2 | 3 |
| 3 | 32 | 3 | 4 |
| 4 | 64 | 4 | 6 |
| 5 | 128 | 5 | 8 |

Configurations: `m1, m2, m3, m1m2, m1m3, m2m3, m1m2m3`, plus `plain`. A checksum
gate (identical to plain) holds for every build. Note: any configuration using
`variants` carries a minimal flatten+harden per body, because distinct variants
only survive the optimizer when hardened — diversity depends on hardening the same
way flattening does.

## Metric

**Median added ns/call vs plain**: for each function, (obfuscated − plain), then the
median across the corpus. A raw average is *not* used because one function
(`fn_sum_primes`, ~27.7 us) is ~85% of the corpus total and its run-to-run variance
swamps the tens-of-ns method overhead. The median of per-function deltas is robust
to those microsecond-scale outliers.

## Reproduce (bench on AC, governor = performance)

```sh
cd experiments/runtime-cost
python3 gen_runtime.py          # build + bench every config x level; enforces the gate
python3 make_runtime_figures.py # -> results/figures/fig_m1..fig_all.svg
```

## Figures

- `fig_m1.svg`, `fig_m2.svg`, `fig_m3.svg` — each method alone.
- `fig_pairs.svg` — the three pairwise combinations.
- `fig_all.svg` — all seven configurations overlaid.

## The finding

M1 (flatten) and M2 (harden) are ~free at runtime and stay flat however hard you
crank them — bogus code never runs, and the opaque predicate is a few ops on the
real path. M3 (variants) is the only method with real runtime cost (~+30 to +42 ns),
because it does work every call (a wall-clock read plus an unpredictable K-way
dispatch), and it grows with K. So the clean rule: **attacker cost scales with all
three knobs; defender cost scales only with method 3.**
