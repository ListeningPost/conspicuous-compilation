use llnv_rust_obf::llnv_obfuscate;
use std::time::Instant;

#[inline(never)]
fn plain(key: u64) -> bool {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325; let mut k = key;
    for _ in 0..8 { h ^= k & 0xff; h = h.wrapping_mul(0x0000_0100_0000_01b3); k >>= 8; }
    (h ^ 0x9e37_79b9_7f4a_7c15) % 97 == 0
}
#[llnv_obfuscate]
fn obf(key: u64) -> bool {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325; let mut k = key;
    for _ in 0..8 { h ^= k & 0xff; h = h.wrapping_mul(0x0000_0100_0000_01b3); k >>= 8; }
    (h ^ 0x9e37_79b9_7f4a_7c15) % 97 == 0
}
#[llnv_obfuscate(jumps = 128, mba_depth = 4)]
fn heavy(key: u64) -> bool {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325; let mut k = key;
    for _ in 0..8 { h ^= k & 0xff; h = h.wrapping_mul(0x0000_0100_0000_01b3); k >>= 8; }
    (h ^ 0x9e37_79b9_7f4a_7c15) % 97 == 0
}
fn time<F: Fn(u64) -> bool>(name: &str, n: u64, f: F) {
    let t = Instant::now();
    let mut acc = 0u64;
    for k in 0..n { if f(std::hint::black_box(k)) { acc += 1; } }
    let d = t.elapsed();
    std::hint::black_box(acc);
    println!("{name:<8} {:>8.2} ns/call  ({acc} hits)", d.as_nanos() as f64 / n as f64);
}
fn main() {
    let n = 50_000_000u64;
    time("plain", n, plain);
    time("obf", n, obf);
    time("heavy", n, heavy);
}
