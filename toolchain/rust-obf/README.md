# llnv-rust-obf

The `#[llnv_obfuscate]` attribute macro: per-function, behaviour-preserving
anti-reverse-engineering for Rust. This is the toolchain behind the paper
*Conspicuous Compilation* (see the [repository root](../../README.md)).

Applied to a function, the macro rewrites its body into a flattened dispatcher
(`loop { match state }`) whose transitions route through an always-true **opaque
predicate**, surrounded by bogus states that never execute, with state constants
**MBA-masked** so the optimizer cannot prune the dead edges. Behaviour is unchanged;
only the compiled representation becomes expensive to decompile.

## Use

```rust
use llnv_rust_obf::llnv_obfuscate;

#[llnv_obfuscate]                                  // default hardening
pub extern "C" fn f(state: &mut [u64; 8], n: u64) -> u64 { /* ... */ }

#[llnv_obfuscate(jumps = 128, mba_depth = 4)]      // heavier
pub extern "C" fn g(state: &mut [u64; 8], n: u64) -> u64 { /* ... */ }
```

Add the dependency by path (as the experiments do):

```toml
[dependencies]
llnv-rust-obf = { path = "../../toolchain/rust-obf" }
```

## Knobs

| Knob | Default | Range | Effect |
|---|--:|---|---|
| `flatten` | `1` | 0/1 | Control-flow flattening + bogus-state CFG inflation (method 1). |
| `harden` | `1` | 0/1 | Opaque-predicate routing + MBA-masked state constants (method 2). |
| `jumps` | `24` | ≤ 4096 | Number of bogus dispatcher states. |
| `mba_depth` | `2` | 1–16 | Depth of the mixed-boolean-arithmetic masking. |
| `variants` | `1` | 1–64 | Runtime-selected diverse bodies (method 3); `K` independently scrambled copies, one chosen per call. |

`flatten=1, harden=0` yields bogus states with clear, foldable constants (flattening without
the anti-pruning layer); `flatten=0, harden=1` applies the opaque predicate and MBA on the
real path only.

## Seeding and reproducibility

State constants are drawn from a seed. Set `LLNV_SEED` (an integer env var read at compile
time) to make builds byte-for-byte reproducible; the experiments pin `LLNV_SEED=7`.

## Build

```bash
cargo build --release          # the macro crate (proc-macro)
cargo run --release -p <demo>  # see demo/ for a runnable example
```

Requires rustc 1.94+. The standard library is never transformed.

## License

[Apache-2.0](../../LICENSE).
