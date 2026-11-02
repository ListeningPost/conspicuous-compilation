// Robustness: the macro must preserve ?, early return, unit return, generics, Result.
use llnv_rust_obf::llnv_obfuscate;

#[llnv_obfuscate]
fn unit_and_early(x: i32) -> () {
    if x < 0 { return; }      // early return
    let _ = x + 1;
}

#[llnv_obfuscate]
fn with_question(s: &str) -> Result<u64, std::num::ParseIntError> {
    let n: u64 = s.parse()?;  // ? operator propagates through the dispatcher
    Ok(n * 2)
}

#[llnv_obfuscate(jumps = 8)]
fn generic_max<T: PartialOrd + Copy>(a: T, b: T) -> T {
    if a > b { a } else { b }
}

#[llnv_obfuscate]
fn borrows(v: &[u8]) -> u8 {       // borrow held across the body
    let mut s = 0u8;
    for &b in v { s = s.wrapping_add(b); }
    s
}

fn main() {
    assert_eq!(unit_and_early(-1), ());
    assert_eq!(unit_and_early(5), ());
    assert_eq!(with_question("21").unwrap(), 42);
    assert!(with_question("xx").is_err());
    assert_eq!(generic_max(3, 9), 9);
    assert_eq!(generic_max(2.5, 1.5), 2.5);
    assert_eq!(borrows(&[1, 2, 3, 250, 10]), 10u8);
    println!("EDGE CASES PASS: ?, early return, unit, generics, borrows all preserved");
}
