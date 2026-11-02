// Selector-uniformity measurement for Method C (runtime-selected diverse variants).
//
// Method C picks which of K diverse bodies runs on a given call with a wall-clock
// time-hash: a MurmurHash3 finalizer over SystemTime nanoseconds, reduced mod K.
// This program reproduces that exact selector expression (see
// toolchain/rust-obf/src/lib.rs, the `__llnv_sel` block) and measures, over N
// successive calls, how often two consecutive calls land on the same body
// (the "consecutive-repeat rate"). A memoryless uniform selector over K bodies
// has an expected consecutive-repeat rate of 1/K.
//
// This is a live-timing measurement: the clock source and loop speed are part of
// what is being characterised, so the exact rate varies run to run. We therefore
// repeat the 10^6-call experiment REPS times per K and report the median rate and
// the observed range, plus a chi-square goodness-of-fit of the body distribution
// against uniform. The result is written to results/selector_uniformity.json.
//
// Build + run (no dependencies):
//   rustc -O experiments/variants-cost/selector_uniformity.rs \
//     -o /tmp/selector_uniformity && /tmp/selector_uniformity

use std::time::{SystemTime, UNIX_EPOCH};

/// The exact selector used by the obfuscation macro: MurmurHash3 finalizer
/// (as implemented in the macro) over the wall clock, reduced mod k.
#[inline(never)]
fn select(k: u64) -> u64 {
    let t = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos() as u64)
        .unwrap_or(0);
    let mut h = std::hint::black_box(t);
    h ^= h >> 33;
    h = h.wrapping_mul(0xff51afd7ed558ccd);
    h ^= h >> 33;
    h % k
}

fn measure(k: u64, n: u64) -> (u64, f64, Vec<u64>) {
    let mut hist = vec![0u64; k as usize];
    let mut prev = select(k);
    hist[prev as usize] += 1;
    let mut repeats = 0u64;
    for _ in 1..n {
        let cur = select(k);
        if cur == prev {
            repeats += 1;
        }
        hist[cur as usize] += 1;
        prev = cur;
    }
    // consecutive-repeat rate over the (n-1) adjacent pairs
    let rate = repeats as f64 / (n - 1) as f64;
    (repeats, rate, hist)
}

/// Chi-square upper-tail critical value at p=0.05 for the degrees of freedom we use.
fn chi2_crit_p05(df: u64) -> f64 {
    match df {
        1 => 3.841,
        3 => 7.815,
        7 => 14.067,
        15 => 24.996,
        31 => 44.985,
        63 => 82.529,
        _ => f64::NAN,
    }
}

fn median(xs: &mut [f64]) -> f64 {
    xs.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let m = xs.len() / 2;
    if xs.len() % 2 == 1 {
        xs[m]
    } else {
        (xs[m - 1] + xs[m]) / 2.0
    }
}

fn main() {
    let n: u64 = 1_000_000;
    let reps: usize = 15;
    let ks: [u64; 6] = [2, 4, 8, 16, 32, 64];

    let mut rows = String::new();
    rows.push_str("  \"n_calls_per_rep\": 1000000,\n");
    rows.push_str(&format!("  \"reps\": {},\n", reps));
    rows.push_str("  \"selector\": \"murmurhash3_finalizer(SystemTime::now nanos) % K\",\n");
    rows.push_str("  \"rows\": [\n");

    let mut headline = String::new();
    let mut headline_rate = String::new();
    for (i, &k) in ks.iter().enumerate() {
        let mut rates = Vec::with_capacity(reps);
        let mut chi2s = Vec::with_capacity(reps);
        let expected = n as f64 / k as f64;
        for _ in 0..reps {
            let (_repeats, rate, hist) = measure(k, n);
            let chi2: f64 = hist
                .iter()
                .map(|&c| {
                    let d = c as f64 - expected;
                    d * d / expected
                })
                .sum();
            chi2s.push(chi2);
            rates.push(rate);
        }
        let rmin = rates.iter().cloned().fold(f64::INFINITY, f64::min);
        let rmax = rates.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let med = median(&mut rates);
        let med_chi2 = median(&mut chi2s);
        rows.push_str(&format!(
            "    {{ \"k\": {}, \"median_chi2_uniform\": {:.2}, \"df\": {}, \"chi2_crit_p05\": {:.2}, \"median_consecutive_repeat_rate\": {:.6}, \"repeat_rate_min\": {:.6}, \"repeat_rate_max\": {:.6}, \"expected_1_over_k\": {:.6} }}{}\n",
            k,
            med_chi2,
            k - 1,
            chi2_crit_p05(k - 1),
            med,
            rmin,
            rmax,
            1.0 / k as f64,
            if i + 1 < ks.len() { "," } else { "" }
        ));
        println!(
            "K={:>2}  median chi2 = {:>5.2} (df={}, crit.05={:.1})  |  repeat-rate median={:.4} range[{:.4},{:.4}] (1/K={:.4})",
            k,
            med_chi2,
            k - 1,
            chi2_crit_p05(k - 1),
            med,
            rmin,
            rmax,
            1.0 / k as f64
        );
        if k == 8 {
            headline = format!("{:.2}", med_chi2);
            headline_rate = format!("{:.3}", med);
        }
    }
    rows.push_str("  ]\n");

    let json = format!(
        "{{\n  \"experiment\": \"selector-uniformity (Method C)\",\n  \"note\": \"median_chi2 is the robust reproducible statistic; consecutive_repeat_rate is a live-timing quantity that varies with CPU/clock state and is reported as a range only\",\n  \"headline_k8_median_chi2_uniform\": {},\n  \"headline_k8_df\": 7,\n  \"headline_k8_chi2_crit_p05\": 14.067,\n  \"headline_k8_median_consecutive_repeat_rate\": {},\n{}}}\n",
        headline, headline_rate, rows
    );

    let out = "experiments/variants-cost/results/selector_uniformity.json";
    std::fs::write(out, json).expect("write results");
    println!("\nwrote {}", out);
    println!("HEADLINE K=8 consecutive-repeat rate = {}", headline);
}
