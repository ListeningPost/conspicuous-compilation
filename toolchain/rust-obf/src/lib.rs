//! LLNV `#[llnv_obfuscate]` — a per-function anti-reverse-engineering attribute
//! macro: a per-function control-flow and constant obfuscator for Rust.
//!
//! Put the attribute on the functions worth protecting:
//!
//! ```ignore
//! use llnv_rust_obf::llnv_obfuscate;
//!
//! #[llnv_obfuscate]                      // default hardening
//! fn verify_license(key: &str) -> bool { /* ... */ }
//!
//! #[llnv_obfuscate(jumps = 128, mba_depth = 4)]   // heavier
//! fn derive_key(pw: &str, salt: &[u8]) -> [u8; 32] { /* ... */ }
//! ```
//!
//! # What it does
//!
//! The function body is wrapped in a flattened dispatcher: a `loop { match st }`
//! state machine. The real body is a single state the machine routes to through
//! an always-true **opaque predicate**, surrounded by `jumps` **bogus states**
//! that are never executed but inflate the control-flow graph (cyclomatic
//! complexity). Every state constant is **MBA-masked** — XOR-ed with nested
//! always-zero mixed-boolean-arithmetic terms — so a decompiler cannot recover
//! the transition targets by constant propagation.
//!
//! The opaque predicate is `(7*a*a - 1) != b*b`, which holds for every integer
//! `a,b` because `7x^2 - 1 == y^2` has no integer solution (6 is a quadratic
//! non-residue mod 7). Operands pass through `core::hint::black_box`, so LLVM
//! cannot fold them and keeps the dead bogus edges in the emitted code; they are
//! masked to 30 bits so `7*a*a-1` and `b*b` stay exact in `u64` and never wrap.
//!
//! # Soundness
//!
//! The real body is kept as ONE dispatcher segment. It is not
//! split across states, because Rust's ownership/borrow rules make moving
//! statements between states unsound in general and a proc-macro has no
//! compile-and-fallback path. Wrapping the whole body is sound for any function:
//! `return`, `?`, and the tail expression all work, because the dispatcher loop
//! is the function's tail expression and the real arm does `break 'llnv body`.
//!
//! # Cost model (honest)
//!
//! Bogus states are unreachable, so they cost binary size and decompiler effort
//! but ~zero runtime. The real path runs the entry predicate plus one `break`:
//! a few `black_box`-barriered integer ops. Apply it to the handful of functions
//! that embody your IP, not hot inner loops. Like the rest of LLNV this is an
//! ECONOMIC, static/automated-analysis defense — a debugger still observes the
//! concrete path and reads the state variable at runtime. See the repo README.
//!
//! # Moving-target seeding
//!
//! State constants are drawn from a seed. `LLNV_SEED` (an integer env var read at
//! compile time) pins them for reproducible builds; unset, the seed is drawn from
//! the wall clock so each build is wired differently — pair with frequent
//! recompiles so analysis of one build never amortizes onto the next.

use proc_macro::TokenStream;
use proc_macro2::{Literal, TokenStream as TS};
use quote::quote;
use std::collections::HashSet;
use syn::parse::Parser;
use syn::{parse_macro_input, punctuated::Punctuated, Expr, ExprLit, ItemFn, Lit, MetaNameValue, Token};

struct Args {
    jumps: u64,
    mba_depth: u32,
    // Independent pass toggles, so each transformation can be measured in
    // isolation. Both default to `true`, so an unqualified `#[llnv_obfuscate]`
    // and the `jumps`/`mba_depth` knobs behave exactly as before.
    //   flatten = control-flow flattening + bogus-state CFG inflation (method 1)
    //   harden  = opaque-predicate routing + MBA-masked state constants (method 2)
    // flatten=1, harden=0 → bogus states with CLEAR constants and a foldable
    //   router: a decompiler can constant-propagate and prune the dead edges.
    // flatten=0, harden=1 → opaque predicate + MBA on the real path only, no
    //   bogus inflation.
    flatten: bool,
    harden: bool,
    // Runtime-selected diverse variants (method 3). With
    // variants>1 the macro emits K independently-flattened, independently-scrambled
    // copies of the body (each with its own entry, state constants, shuffle and
    // bogus padding) behind an outer dispatcher that hashes the wall clock at call
    // time and selects one. Across runs a different jumbled body executes for the
    // same observable behaviour, so which variant ran is not statically determined.
    // Each variant here is a distinct full body. Default 1 = single body (no outer selector).
    variants: u64,
}

impl Default for Args {
    fn default() -> Self {
        Args { jumps: 24, mba_depth: 2, flatten: true, harden: true, variants: 1 }
    }
}

fn parse_args(attr: TokenStream) -> Args {
    let mut a = Args::default();
    if attr.is_empty() {
        return a;
    }
    let parser = Punctuated::<MetaNameValue, Token![,]>::parse_terminated;
    let parsed = match parser.parse(attr) {
        Ok(p) => p,
        Err(_) => return a,
    };
    for nv in parsed {
        let key = nv.path.get_ident().map(|i| i.to_string()).unwrap_or_default();
        if let Expr::Lit(ExprLit { lit: Lit::Int(li), .. }) = nv.value {
            if let Ok(v) = li.base10_parse::<u64>() {
                match key.as_str() {
                    "jumps" => a.jumps = v.min(4096),
                    "mba_depth" => a.mba_depth = (v as u32).clamp(1, 16),
                    "flatten" => a.flatten = v != 0,
                    "harden" => a.harden = v != 0,
                    "variants" => a.variants = v.clamp(1, 64),
                    _ => {}
                }
            }
        }
    }
    a
}

// splitmix64 — small deterministic PRNG for picking distinct state constants.
struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
}

fn seed_rng(name: &str) -> Rng {
    let base = match std::env::var("LLNV_SEED") {
        Ok(s) => s.trim().parse::<u64>().unwrap_or(0xA5A5_5A5A),
        Err(_) => std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos() as u64)
            .unwrap_or(0x1234_5678),
    };
    let mut h: u64 = 1469598103934665603;
    for b in name.bytes() {
        h ^= b as u64;
        h = h.wrapping_mul(1099511628211);
    }
    Rng(base ^ h)
}

fn u64lit(v: u64) -> Literal {
    Literal::u64_suffixed(v)
}

// Emit a token stream that evaluates to `val` but is not constant-foldable:
// `( val ^ __llnv_mz(s1) ^ __llnv_mz(s2) ... )`, each `__llnv_mz` always 0.
fn mba(val: u64, rng: &mut Rng, depth: u32) -> TS {
    let vlit = u64lit(val);
    let mut terms = Vec::new();
    for _ in 0..depth {
        let s = u64lit(rng.next() & 0x3fff_ffff);
        terms.push(quote! { ^ __llnv_mz(#s) });
    }
    quote! { ( #vlit #(#terms)* ) }
}

// A state-constant emitter that respects the `harden` toggle. With hardening on,
// the value is MBA-masked (not constant-foldable). With hardening off, it is a
// plain literal a decompiler can constant-propagate — the control for measuring
// flattening WITHOUT the anti-pruning layer.
fn maskval(val: u64, rng: &mut Rng, depth: u32, harden: bool) -> TS {
    if harden {
        mba(val, rng, depth)
    } else {
        let v = u64lit(val);
        quote! { ( #v ) }
    }
}

// The dispatcher router predicate. Hardened: the always-true opaque predicate,
// barriered by black_box so neither the compiler nor a decompiler can fold the
// dead edge away. Unhardened: a literal `true` the optimizer folds, so the dead
// arm is pruned — exactly the behaviour we want to contrast against.
fn router(a: Literal, b: Literal, harden: bool) -> TS {
    if harden {
        quote! { __llnv_opaque(#a, #b) }
    } else {
        quote! { true }
    }
}

// Build ONE flattened+hardened dispatcher block for `body`. Each call draws fresh
// state constants from `rng`/`seen`. `jumps` is the bogus-state count for THIS body
// (the variant path passes a different value per variant, so bodies differ in size).
// With `shuffle` set, the dead-edge topology is randomised and the match arms are
// emitted in a random order, so variant bodies are not merely re-numbered copies of
// one skeleton but materially different control-flow graphs.
fn build_dispatcher(rng: &mut Rng, seen: &mut HashSet<u64>, args: &Args, body: &TS,
                    jumps: u64, shuffle: bool) -> TS {
    let band_lo = 1u64 << 20;
    let band_hi = 1u64 << 21;
    let mut fresh = |rng: &mut Rng| -> u64 {
        loop {
            let v = band_lo + (rng.next() % (band_hi - band_lo));
            if seen.insert(v) {
                return v;
            }
        }
    };
    let harden = args.harden;
    let depth = args.mba_depth;
    let entry = fresh(rng);
    let real = fresh(rng);
    let bogus: Vec<u64> = if args.flatten {
        (0..jumps).map(|_| fresh(rng)).collect()
    } else {
        Vec::new()
    };

    let entry_pat = u64lit(entry);
    let real_pat = u64lit(real);
    let entry_init = maskval(entry, rng, depth, harden);
    let (ea, eb) = (u64lit(rng.next()), u64lit(rng.next()));
    let entry_cond = router(ea, eb, harden);
    let entry_real = maskval(real, rng, depth, harden);
    let entry_bogus = maskval(*bogus.first().unwrap_or(&real), rng, depth, harden);

    let mut bogus_arms = Vec::new();
    for (i, &b) in bogus.iter().enumerate() {
        let pat = u64lit(b);
        let a = u64lit(rng.next());
        let bb = u64lit(rng.next());
        let cond = router(a, bb, harden);
        let onward = maskval(real, rng, depth, harden);
        // Dead-edge target: a fixed ring by default; a random OTHER bogus state when
        // shuffling, so the never-taken topology differs from variant to variant.
        let alt_idx = if shuffle && bogus.len() > 1 {
            let mut j = (rng.next() as usize) % bogus.len();
            if j == i { j = (j + 1) % bogus.len(); }
            j
        } else {
            (i + 1) % bogus.len().max(1)
        };
        let alt = maskval(bogus[alt_idx], rng, depth, harden);
        bogus_arms.push(quote! {
            #pat => { __llnv_st = if #cond { #onward } else { #alt }; }
        });
    }
    let default_real = maskval(real, rng, depth, harden);

    // Collect real + entry + bogus arms; with `shuffle`, emit them in a random order
    // (the wildcard default stays last). Order is semantically irrelevant for disjoint
    // constant patterns, but it changes each variant's emitted code layout.
    let entry_arm = quote! { #entry_pat => { __llnv_st = if #entry_cond { #entry_real } else { #entry_bogus }; } };
    let real_arm = quote! { #real_pat => break 'llnv_loop #body, };
    let mut arms: Vec<TS> = vec![entry_arm, real_arm];
    arms.extend(bogus_arms);
    if shuffle {
        for i in (1..arms.len()).rev() {
            let j = (rng.next() as usize) % (i + 1);
            arms.swap(i, j);
        }
    }

    quote! {
        {
            #[allow(unused, clippy::all, unused_parens)]
            let __llnv_mz = |s: u64| -> u64 {
                let m = core::hint::black_box(s) & 0x3fff_ffff;
                (m.wrapping_mul(m.wrapping_add(1))) & 1
            };
            #[allow(unused, clippy::all, unused_parens)]
            let __llnv_opaque = |a: u64, b: u64| -> bool {
                let a = core::hint::black_box(a) & 0x3fff_ffff;
                let b = core::hint::black_box(b) & 0x3fff_ffff;
                (7u64.wrapping_mul(a).wrapping_mul(a).wrapping_sub(1)) != b.wrapping_mul(b)
            };
            let mut __llnv_st: u64 = #entry_init;
            #[allow(unused_parens)]
            'llnv_loop: loop {
                match __llnv_st {
                    #(#arms)*
                    _ => { __llnv_st = #default_real; }
                }
            }
        }
    }
}

#[proc_macro_attribute]
pub fn llnv_obfuscate(attr: TokenStream, item: TokenStream) -> TokenStream {
    let args = parse_args(attr);
    let func = parse_macro_input!(item as ItemFn);
    let mut rng = seed_rng(&func.sig.ident.to_string());
    let mut seen = HashSet::new();

    let block = &func.block;
    let body_ts: TS = quote! { #block };
    let vis = &func.vis;
    let sig = &func.sig;
    let attrs = &func.attrs;

    let new_body = if args.variants <= 1 {
        // Single body (methods 1 and 2 only) — unchanged behaviour (fixed topology,
        // no arm shuffle), so builds without variants are byte-for-byte as before.
        build_dispatcher(&mut rng, &mut seen, &args, &body_ts, args.jumps, false)
    } else {
        // Method 3: K independently-flattened bodies, one chosen per call by a
        // wall-clock time-hash. Each variant gets its OWN bogus-state count drawn
        // around the dial, a randomised dead-edge topology, and a shuffled arm order,
        // so the K bodies are materially different CFGs, not re-numbered copies.
        let k = args.variants;
        let base = args.jumps.max(1);
        let jlo = (base - base / 2).max(1);
        let jhi = base + base / 2;
        let pick_jumps = |rng: &mut Rng| -> u64 {
            if args.flatten && jhi > jlo { jlo + (rng.next() % (jhi - jlo + 1)) } else { base }
        };
        let arms: Vec<TS> = (0..k)
            .map(|i| {
                let j_i = pick_jumps(&mut rng);
                let disp = build_dispatcher(&mut rng, &mut seen, &args, &body_ts, j_i, true);
                let pat = u64lit(i);
                quote! { #pat => #disp }
            })
            .collect();
        let j_d = pick_jumps(&mut rng);
        let default_disp = build_dispatcher(&mut rng, &mut seen, &args, &body_ts, j_d, true);
        let klit = u64lit(k);
        quote! {
            {
                // Time-hashed variant selector: a MurmurHash3 finalizer over the
                // wall clock picks which diverse body runs on this call.
                #[allow(unused_parens)]
                let __llnv_sel: u64 = {
                    let __t = ::std::time::SystemTime::now()
                        .duration_since(::std::time::UNIX_EPOCH)
                        .map(|d| d.as_nanos() as u64)
                        .unwrap_or(0);
                    let mut __h = core::hint::black_box(__t);
                    __h ^= __h >> 33;
                    __h = __h.wrapping_mul(0xff51afd7ed558ccd);
                    __h ^= __h >> 33;
                    __h % #klit
                };
                match __llnv_sel {
                    #(#arms,)*
                    _ => #default_disp,
                }
            }
        }
    };

    quote! {
        #(#attrs)*
        #[inline(never)]
        #vis #sig #new_body
    }
    .into()
}
