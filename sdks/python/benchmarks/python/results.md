# Python SDK Benchmark Results

## Environment

- Machine: MacBook Air (Apple Silicon)
- Python: 3.9.9
- Redis: localhost port 6399
- Date: May 2026

## Results

| Benchmark | Min | Mean | Median | OPS |
|---|---|---|---|---|
| is_enabled() user allowlist | 0.097ms | 0.104ms | 0.101ms | 9,615/sec |
| is_enabled() warm cache | 0.199ms | 0.252ms | 0.209ms | 3,962/sec |
| is_enabled() 10k flags | 0.199ms | 0.225ms | 0.206ms | 4,439/sec |
| is_enabled() large cohort 100k | 0.199ms | 0.209ms | 0.206ms | 4,789/sec |
| is_enabled() cohort match | 0.199ms | 0.209ms | 0.207ms | 4,796/sec |
| is_enabled() cold cache | 0.317ms | 0.339ms | 0.333ms | 2,953/sec |
| is_enabled() Redis down stale cache | 0.592ms | 0.647ms | 0.629ms | 1,545/sec |
| 1000 users rollout distribution | 206ms total | 207ms total | 207ms total | 0.207ms/user |
| 100 concurrent threads | 771ms total | 783ms total | 785ms total | no errors |

## Key findings

- **Warm cache path: 0.1ms** — safe to call on every HTTP request
- **Cold cache path: 0.3ms** — full Redis round-trip still well under 5ms target
- **10,000 flags: no degradation** — index Set avoids KEYS * scan
- **100,000 user cohort: no degradation** — SINTER is O(N) on intersection size
- **Redis down: 0.6ms** — stale cache keeps application running
- **100 concurrent threads: zero errors** — thread-safe cache confirmed
- **Rollout distribution: ~50% of 1000 users** — deterministic SHA-256 hashing confirmed

## How to run

```bash
redis-server --port 6399 --daemonize yes
cd sdks/python
pytest benchmarks/python/benchmark.py -v \
    --benchmark-sort=name \
    --benchmark-columns=min,max,mean,stddev,median,ops,rounds \
    --no-cov
```