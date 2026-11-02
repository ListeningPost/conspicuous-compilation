#!/usr/bin/env bash
# Re-measure every experiment that feeds a graph in docs/conspicuous-compilation-final.pdf,
# from a clean build, with the integrity-gated harness (median of 10, explicit
# OK/FAIL per decompile, DCDONE sentinel). Any condition that does not decompile
# cleanly aborts that experiment instead of emitting silently bogus timings.
#
# Timing is wall-clock sensitive: run on AC power with the CPU governor pinned to
# `performance`. Prereq: GHIDRA_HEADLESS points at analyzeHeadless (default
# /opt/ghidra_12.1.4_PUBLIC/support/analyzeHeadless).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
TS="$(date +%Y%m%d-%H%M%S)"
log(){ printf '\n========== %s ==========\n' "$*"; }

archive(){ # move prior results aside, non-destructively, and force a clean build
  local d="$1"
  [ -d "$ROOT/$d/results" ] && mv "$ROOT/$d/results" "$ROOT/$d/results.bak-$TS" && echo "archived $d/results -> results.bak-$TS"
  rm -rf "$ROOT/$d/build"/*/target 2>/dev/null || true   # force clean recompile
}

# ---- decompile-cost: build + runtime bench + gated decompile sweep + figures ----
log "decompile-cost"
archive decompile-cost
( cd "$ROOT/decompile-cost"
  python3 gen_build.py
  mkdir -p results/raw/bench
  for b in results/bin/corpus_*; do c=$(basename "$b" | sed 's/corpus_//'); "$b" bench > "results/raw/bench/$c.txt"; done
  ./run_sweep.sh
  python3 aggregate.py
  python3 make_figures.py
)

# ---- variants-cost: build + gated decompile sweep (aggregate emits its figure) ----
log "variants-cost"
archive variants-cost
( cd "$ROOT/variants-cost"
  python3 gen_variants.py
  ./run_variants.sh
  python3 aggregate_variants.py
  ./run_selector_uniformity.sh   # Method C selector uniformity (chi-square) -> results/selector_uniformity.json
)

# ---- breadth-cost: build + gated decompile sweep (aggregate emits its figure) ----
log "breadth-cost"
archive breadth-cost
( cd "$ROOT/breadth-cost"
  python3 gen_breadth.py
  ./run_breadth.sh
  python3 aggregate_breadth.py
)

log "ALL EXPERIMENTS RE-MEASURED — every condition passed the integrity gate"
echo "New results under each experiment's results/; prior run preserved as results.bak-$TS"
echo "Figures refreshed: decompile-cost/results/figures, variants-cost/results/figures, breadth-cost/results/figures"
