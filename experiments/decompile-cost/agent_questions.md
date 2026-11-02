# agent_questions.md

A FAQ for an AI agent (or a person) picking up this experiment cold. It records
*why* the experiment is shaped the way it is, so you can follow along and extend
it without reconstructing every decision. Answers are written to be safe to act
on. When in doubt, the correctness gate and the raw logs are ground truth; prose
(including this file) is not.

---

### Q. In one sentence, what is this?

A controlled measurement of how much **automated static reverse engineering**
(decompiler wall-clock) a source-level obfuscation costs an attacker, and how
little runtime it costs the defender, across a corpus of functions and a sweep of
the obfuscation dial.

### Q. What is "conspicuous compilation"?

Obfuscating the **compiled binary** so that automated analysis is expensive, while
leaving the source readable and behaviour identical. It is "conspicuous" because
the output advertises that it was transformed — the goal is *expense*, not
hiding. Contrast with source-level obfuscation, which mangles the source itself.

### Q. Why Rust only?

Because this specific experiment needs a *clean per-function baseline*, and Rust
gives one: the optimizer keeps our annotated functions as standalone symbols, so
"plain vs obfuscated" compares the same function. Compilation models that inline
these small functions out of existence — where the only pragma that stops inlining
also makes the obfuscator skip the function — cannot produce an honest per-function
decompile baseline. Mixing granularities would mislead, so this experiment is Rust-only by
design, not by omission.

### Q. What are "method 1" and "method 2"?

- **Method 1 = control-flow flattening + bogus states.** The body becomes a
  dispatcher `loop { match state }` with `jumps` unreachable decoy states.
- **Method 2 = opaque-predicate routing + MBA-masked constants.** Transitions go
  through an always-true predicate `7a²−1 ≠ b²` and the state numbers are
  XOR-masked with always-zero arithmetic, both barriered by `black_box`.

They live in the same macro but are independently toggled with `flatten=` and
`harden=`. Defaults are both-on, so existing builds are unchanged.

### Q. Why measure them separately instead of just "on vs off"?

Because the interesting claim is *mechanistic*: method 2 is what makes method 1
**survive the optimizer**. Flattening alone emits dead edges the compiler proves
unreachable and deletes, so it should cost the attacker ~nothing. Hardening
removes that proof, so the edges persist and the decompiler must grind through
them. Measuring the two alone and together is how you show the effect is a
genuine interaction, not either pass on its own.

### Q. What result should I expect, and what would falsify the claim?

Expected: `m1_j*` (flatten only) ≈ `plain` in size and decompile time at every
jump count, `m2_d2` a modest bump, and `both_j*` rising with `jumps`. Already
visible in binary size: `m1_*` is flat at ~455 KB (== plain) across all jump
counts; `both_*` grows 488 KB → 1.29 MB as jumps go 8 → 256.

**Falsification:** if `both_j*` decompile time does **not** rise with `jumps`, the
hardening isn't preventing pruning and the headline claim is wrong — report that.
If `m1_j*` decompile time *does* rise, then flattening alone already helps and the
"method 2 protects method 1" framing is wrong. Either outcome is publishable; do
not bend the data toward the expected one.

### Q. What is the checksum gate and why does it matter?

Every condition's binary prints `CHECKSUM=17786522303719185614`. It is the XOR-fold
of all 16 functions over a fixed input sweep. If any obfuscation changed behaviour,
the checksum would differ and `gen_build.py` aborts. It is the proof that we are
measuring the cost of *representing the same computation*, not of computing
something else. Never report a number from a condition whose checksum differs.

### Q. Which attacker does this model — and which does it NOT?

Models: a **static, automated decompiler** (Ghidra headless) with no human in the
loop — the scalable, cheap attacker that motivates the work. Does **not** model a
**dynamic** attacker: a debugger that runs the binary walks the one real path and
reads the state variable directly, defeating flattening. State this in any writeup.
Claiming security against a debugger would be false.

### Q. Why isn't the runtime overhead growing with the dial?

Bogus states are **unreachable** — they cost binary size and decompiler effort but
never execute. The only added runtime is the entry opaque predicate plus one
branch: a near-constant ~5 ns. So expect large runtime *ratios* on trivial
functions (6 ns vs 1 ns) and negligible *absolute* cost on functions doing real
work, and no growth with `jumps`. The decoupling — attacker cost scales with the
dial, defender cost does not — is a feature, and it is the honest framing.

### Q. I want to extend this. What is safe to change?

- Add functions to `corpus.rs.in` (keep them pure, `#[no_mangle] extern "C"`, same
  signature). Re-run `gen_build.py`; the gate will re-validate.
- Add a second decompiler (angr, Binary Ninja) over `results/bin/*` to kill the
  "it's a Ghidra artifact" objection. Write a sibling of `DecompCorpus.java`.
- Add jump levels or `mba_depth` levels in `gen_build.py:conditions()`.

### Q. What must I NOT do?

- Do not edit the obfuscation passes and re-measure in the same breath without
  re-running the gate and re-recording `env.lock` and sha256s. Stale numbers are
  how papers get retracted.
- Do not invent any number the logs do not contain. If a measurement doesn't
  exist, say "future work".
- Do not average decompile *times* across functions that differ 1000× in size;
  summarise **per-function ratios** (median), as `aggregate.py` does.
