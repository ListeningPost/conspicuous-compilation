# Contributing

Contributions are welcome from humans and AI agents alike. This work is openly
AI-assisted, and we think the best way to build defenses against agent-driven reverse
engineering is to build them in the open, with anyone who wants to help.

## The most valuable contribution: reproduce and challenge the numbers

Before anything else — **run the experiments on your own machine and check the results.**
Don't take the paper's numbers on faith.

```bash
./experiments/rerun_experiments.sh
```

Run on AC power with the CPU governor pinned to `performance`, with Ghidra's
`analyzeHeadless` reachable (`GHIDRA_HEADLESS` or on `PATH`). Each run is pinned by
`LLNV_SEED=7` and records SHA-256 for every analyzed binary. If your numbers differ from
`results/summary.md`, that is interesting — open an issue with your environment
(CPU, rustc, Ghidra version) and the `results/` output.

## Good directions

- **New transformation methods** that raise attacker cost without runtime cost.
- **A second decompiler** beyond Ghidra, to strengthen external validity.
- **A larger / more varied corpus** than the sixteen functions used here.
- **Tighter measurement** — better isolation, more samples, alternative cost metrics.
- **Analysis that breaks our assumptions** — show where the super-linear growth fails.

## Ground rules

- Keep the fixed-output **correctness gate** intact: every obfuscated build must compute
  the identical checksum as plain. A change that alters behaviour is a bug, not an
  obfuscation.
- Keep the measurement **integrity gates** intact: the decompile harness must verify every
  decompile completed (OK/FAIL + `DCDONE` sentinel); never report a run that failed the gate.
- Report numbers honestly. State your environment. Don't hand-tune a figure.

## Scope

This repository is the Rust study behind the paper. Please keep contributions Rust-focused
unless you are proposing a clearly-scoped new experiment.
