# Breadth sweep — summary

Per-function setting fixed at `jumps=64, mba_depth=2`; N = number of obfuscated functions.
Per-N checksum gate held (plain and obf identical at each N).

| N | plain decompile | obf decompile | obf/plain |
|--:|--:|--:|--:|
| 1 | 0.00s | 0.12s | 40.67x |
| 2 | 0.01s | 0.28s | 46.33x |
| 4 | 0.01s | 0.60s | 39.87x |
| 8 | 0.03s | 1.16s | 42.85x |
| 16 | 0.04s | 2.22s | 63.46x |
| 32 | 0.08s | 4.46s | 55.77x |
| 48 | 0.12s | 6.89s | 56.02x |
| 64 | 0.23s | 9.30s | 40.27x |
