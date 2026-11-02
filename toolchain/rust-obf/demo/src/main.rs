// Showcase: identical logic, one plain and one hardened with #[llnv_obfuscate].
// Build through the normal cargo/LLVM backend: `cargo build --release`.
use llnv_rust_obf::llnv_obfuscate;

// A small proprietary-ish routine: a keyed check an attacker would want to read.
#[inline(never)]
fn license_ok_plain(key: u64) -> bool {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    let mut k = key;
    for _ in 0..8 {
        h ^= k & 0xff;
        h = h.wrapping_mul(0x0000_0100_0000_01b3);
        k >>= 8;
    }
    (h ^ 0x9e37_79b9_7f4a_7c15) % 97 == 0
}

#[llnv_obfuscate]
fn license_ok_obf(key: u64) -> bool {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    let mut k = key;
    for _ in 0..8 {
        h ^= k & 0xff;
        h = h.wrapping_mul(0x0000_0100_0000_01b3);
        k >>= 8;
    }
    (h ^ 0x9e37_79b9_7f4a_7c15) % 97 == 0
}

#[llnv_obfuscate(jumps = 128, mba_depth = 4)]
fn license_ok_heavy(key: u64) -> bool {
    let mut h: u64 = 0xcbf2_9ce4_8422_2325;
    let mut k = key;
    for _ in 0..8 {
        h ^= k & 0xff;
        h = h.wrapping_mul(0x0000_0100_0000_01b3);
        k >>= 8;
    }
    (h ^ 0x9e37_79b9_7f4a_7c15) % 97 == 0
}

fn main() {
    // Equivalence check across many inputs: plain == obf == heavy, always.
    let mut mism = 0u64;
    let mut hits = 0u64;
    for key in 0u64..2_000_000 {
        let p = license_ok_plain(key);
        let o = license_ok_obf(key);
        let hv = license_ok_heavy(key);
        if p != o || p != hv {
            mism += 1;
        }
        if p {
            hits += 1;
        }
    }
    println!("checked 2000000 keys: mismatches={mism} valid_keys={hits}");
    if mism == 0 {
        println!("EQUIVALENT: obfuscated behavior matches plain exactly");
    } else {
        println!("BUG: {mism} mismatches");
        std::process::exit(1);
    }
}
