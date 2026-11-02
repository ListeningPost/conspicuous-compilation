#!/usr/bin/env bash
# Ghidra-decompile every breadth-condition binary, timing each function K times.
# Every log is integrity-gated (see verify_log).
set -euo pipefail
HS="$(cd "$(dirname "$0")" && pwd)"
GHIDRA="${GHIDRA_HEADLESS:-/opt/ghidra_12.1.4_PUBLIC/support/analyzeHeadless}"
PROJ="${TMPDIR:-/tmp}/llnv-breadth-proj"; mkdir -p "$PROJ" "$HS/results/raw"
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
for bin in "$HS"/results/bin/corpus_*; do
  c=$(basename "$bin" | sed 's/corpus_//')
  echo "[decompile] $c"
  log="$HS/results/raw/decomp_$c.log"
  /usr/bin/time -v env -i PATH=/usr/bin:/bin:/usr/local/bin "$GHIDRA" "$PROJ" "p_$c" \
    -import "$bin" -overwrite -scriptPath "$HS/harness" -postScript DecompCorpus.java -deleteProject \
    > "$log" 2>&1
  verify_log "$log" "$c" || fail=1
done
if [ "$fail" -ne 0 ]; then
  echo "sweep FAILED integrity gate — do not aggregate these logs" >&2; exit 1; fi
echo "done -> results/raw/decomp_*.log (all conditions passed integrity gate)"
