#!/usr/bin/env bash
# Measure Method C's selector uniformity and write the committed artifact.
# Reproduces the exact macro selector (MurmurHash3 finalizer over SystemTime
# nanoseconds, mod K); reports the reproducible statistic (chi-square goodness-of-fit
# of the body distribution against uniform) plus the live-timing consecutive-repeat
# rate as a range. See selector_uniformity.rs for details.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$here/results"
bin="$(mktemp -d)/selector_uniformity"
rustc -O "$here/selector_uniformity.rs" -o "$bin"
cd "$here/../.."   # repo root, so the artifact path in the program resolves
"$bin"
