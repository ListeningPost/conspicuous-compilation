#!/usr/bin/env bash
# Drive Ghidra headless over every built condition binary, decompiling each
# corpus function K times and logging per-function median decompile time.
# Prereq: python3 gen_build.py has produced results/bin/corpus_*.
# Every log is integrity-gated (see verify_log): a condition whose decompile did
# not complete for all functions aborts the sweep rather than yielding silently
# bogus timings.
set -euo pipefail

HS="$(cd "$(dirname "$0")" && pwd)"
GHIDRA="${GHIDRA_HEADLESS:-/opt/ghidra_12.1.4_PUBLIC/support/analyzeHeadless}"
PROJ="${TMPDIR:-/tmp}/llnv-decompile-sweep-proj"
mkdir -p "$PROJ" "$HS/results/raw"

CONDS=(plain m1_j8 m1_j16 m1_j32 m1_j64 m1_j128 m1_j256 m2_d2 \
       both_j8_d2 both_j16_d2 both_j32_d2 both_j64_d2 both_j128_d2 \
       both_j256_d2 both_j256_d4)

# --- integrity gate -----------------------------------------------------------
# Ghidra's analyzeHeadless exits 0 even when a post-script errors or emits
# nothing, so exit status alone proves nothing. Gate on our own evidence: a
# DCDONE sentinel with ok==total>0, every DC row OK, and no DCERR/FAIL lines.
verify_log() {
  local log="$1" cond="$2" done_line ok total dc_ok dc_fail dcerr
  done_line=$(grep -oE 'DCDONE [0-9]+ [0-9]+' "$log" | tail -1 || true)
  if [ -z "$done_line" ]; then
    echo "  INTEGRITY FAIL [$cond]: no DCDONE sentinel — run did not finish" >&2; return 1; fi
  ok=$(awk '{print $2}' <<<"$done_line"); total=$(awk '{print $3}' <<<"$done_line")
  dc_ok=$(grep -cE 'DC fn_[A-Za-z0-9_]+ OK '   "$log" || true)
  dc_fail=$(grep -cE 'DC fn_[A-Za-z0-9_]+ FAIL ' "$log" || true)
  dcerr=$(grep -cE '> DCERR |^DCERR '          "$log" || true)
  if [ "$total" -eq 0 ]; then
    echo "  INTEGRITY FAIL [$cond]: zero fn_ functions decompiled" >&2; return 1; fi
  if [ "$ok" -ne "$total" ] || [ "$dc_fail" -ne 0 ] || [ "$dcerr" -ne 0 ] || [ "$dc_ok" -ne "$total" ]; then
    echo "  INTEGRITY FAIL [$cond]: ok=$ok total=$total ok_rows=$dc_ok fail_rows=$dc_fail errs=$dcerr" >&2; return 1; fi
  echo "  integrity OK [$cond]: $ok/$total functions decompiled cleanly"
}
# -----------------------------------------------------------------------------
fail=0
for c in "${CONDS[@]}"; do
  bin="$HS/results/bin/corpus_$c"
  [ -f "$bin" ] || { echo "missing $bin — run gen_build.py first" >&2; exit 1; }
  echo "[decompile] $c"
  log="$HS/results/raw/decomp_$c.log"
  # env -i isolates Ghidra from inherited env; /usr/bin/time records wall clock + RSS.
  /usr/bin/time -v env -i PATH=/usr/bin:/bin:/usr/local/bin "$GHIDRA" "$PROJ" "p_$c" \
    -import "$bin" -overwrite \
    -scriptPath "$HS/harness" -postScript DecompCorpus.java -deleteProject \
    > "$log" 2>&1
  verify_log "$log" "$c" || fail=1
done
if [ "$fail" -ne 0 ]; then
  echo "sweep FAILED integrity gate — do not aggregate these logs" >&2; exit 1; fi
echo "sweep complete -> results/raw/decomp_*.log (all conditions passed integrity gate)"
