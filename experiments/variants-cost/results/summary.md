# Variants (method 3) sweep — summary

Per-variant setting fixed at `flatten=1, harden=1, jumps=8, mba_depth=1`; K = diverse bodies per function.
Checksum gate `CHECKSUM=17786522303719185614` held for every K (behaviour unchanged).
Plain-baseline decompile: 0.06s.

| K | size (KB) | decompile | x vs plain |
|--:|--:|--:|--:|
| 1 | 480 | 0.25s | 4.55x |
| 2 | 502 | 0.50s | 9.11x |
| 4 | 547 | 1.04s | 19.0x |
| 8 | 626 | 2.28s | 41.44x |
| 16 | 794 | 5.43s | 98.67x |
| 32 | 1139 | 13.78s | 250.49x |
| 64 | 1817 | 38.73s | 704.18x |
