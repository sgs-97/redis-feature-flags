# Java SDK Benchmark Results

## Environment

- Machine: MacBook Air (Apple Silicon)
- Java: 17 (Temurin)
- Redis: localhost port 6379
- Date: May 2026

## Results

| Benchmark | Min | Mean | p50 | p95 | p99 | OPS |
|---|---|---|---|---|---|---|
| isEnabled() user allowlist | 0.014ms | 0.020ms | 0.020ms | 0.024ms | 0.030ms | 49,549/sec |
| isEnabled() warm cache | 0.033ms | 0.041ms | 0.041ms | 0.046ms | 0.054ms | 24,283/sec |
| isEnabled() cohort match | 0.034ms | 0.044ms | 0.043ms | 0.050ms | 0.059ms | 22,955/sec |
| isEnabled() cold cache | 0.046ms | 0.063ms | 0.062ms | 0.070ms | 0.082ms | 15,885/sec |
| rollout distribution 1000 users | 42.3ms total | 0.042ms/user | — | — | — | — |
| 100 concurrent threads | 2338ms total | — | — | — | — | 0 errors |

## Key findings

- **Warm cache: 0.041ms — 24,283 ops/sec** 
- **Cold cache: 0.063ms — 15,885 ops/sec** — full Redis round-trip under 0.1ms
- **User allowlist: 0.020ms — 49,549 ops/sec** — fastest path
- **Cohort match: 0.044ms** — SINTER overhead negligible
- **1000 users rollout: 492/1000 true** — deterministic SHA-256 confirmed ~50%
- **100 concurrent threads: zero errors** — thread-safe ConcurrentHashMap confirmed

## How to run

```bash
cd sdks/java
mvn test -Dtest=BenchmarkTest
```