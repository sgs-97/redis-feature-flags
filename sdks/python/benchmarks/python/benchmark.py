"""
Stress benchmarks for redis-feature-flags Python SDK.

Tests:
  - is_enabled() warm cache      → flag data already in local cache
  - is_enabled() cold cache      → fetches from real Redis each time
  - is_enabled() Redis down      → stale cache fallback
  - is_enabled() concurrent      → 100 threads simultaneously
  - is_enabled() 10k flags       → large flag count
  - is_enabled() 100k cohort     → large cohort membership

Run:
    redis-server --port 6399 --daemonize yes
    cd sdks/python
    pytest benchmarks/python/benchmark.py -v \
        --benchmark-sort=name \
        --benchmark-columns=min,max,mean,stddev,median,iq r,ops,rounds \
        --benchmark-histogram
"""

from __future__ import annotations

import threading
import time
import pytest
import redis

from redis_feature_flags import FeatureFlags
from redis_feature_flags.cache import LocalCache
from redis_feature_flags.schema import SchemaKeys
from redis_feature_flags.evaluator import Evaluator

# ── Config ─────────────────────────────────────────────────────

REDIS_PORT = 6399
REDIS_HOST = "localhost"
ENV = "benchmark"


# ── Fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def redis_client():
    """Real Redis on port 6399."""
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip(
            f"Redis not running on port {REDIS_PORT}. "
            f"Start with: redis-server --port {REDIS_PORT} --daemonize yes"
        )
    return client


@pytest.fixture(scope="session")
def flags(redis_client):
    """FeatureFlags instance for benchmarks."""
    f = FeatureFlags(redis_client, env=ENV, cache_ttl=30)
    return f


@pytest.fixture(autouse=True, scope="session")
def setup_benchmark_data(redis_client, flags):
    """
    Pre-load all data needed for benchmarks.
    Runs once before all benchmark tests.
    """
    # flush benchmark namespace
    for key in redis_client.keys(f"ff:{ENV}:*"):
        redis_client.delete(key)

    # create standard test flag
    flags.create("bench_flag", rollout=50)
    flags.enable("bench_flag")

    # create flag with user allowlist
    flags.create("allowlist_flag", rollout=0)
    flags.enable("allowlist_flag")
    flags.add_user("allowlist_flag", "alice")

    # create cohort flag
    flags.create("cohort_flag", rollout=0)
    flags.enable("cohort_flag")
    flags.create_cohort("bench-cohort")
    flags.add_to_cohort("bench-cohort", "alice")
    flags.add_cohort_to_flag("cohort_flag", "bench-cohort")

    # create 10k flags for large flag count test
    pipe = redis_client.pipeline()
    for i in range(10_000):
        flag_name = f"flag_{i}"
        pipe.hset(f"ff:{ENV}:flag:{flag_name}", mapping={
            "enabled": "1",
            "rollout": "50",
            "expires_at": "0",
            "flag_version": "1",
            "created_at": str(int(time.time())),
            "updated_at": str(int(time.time())),
            "created_by": "benchmark",
            "updated_by": "benchmark",
        })
        pipe.sadd(f"ff:{ENV}:flags:__index__", flag_name)
    pipe.execute()

    # add 100k users to large cohort
    flags.create_cohort("large-cohort")
    flags.create("large_cohort_flag", rollout=0)
    flags.enable("large_cohort_flag")
    flags.add_cohort_to_flag("large_cohort_flag", "large-cohort")
    pipe = redis_client.pipeline()
    for i in range(100_000):
        pipe.sadd(f"ff:{ENV}:cohort:large-cohort", f"user_{i}")
        pipe.sadd(f"ff:{ENV}:user:user_{i}:cohorts", "large-cohort")
    pipe.execute()

    yield

    # cleanup
    for key in redis_client.keys(f"ff:{ENV}:*"):
        redis_client.delete(key)


# ── Benchmarks ─────────────────────────────────────────────────


def test_is_enabled_warm_cache(benchmark, flags):
    """
    Benchmark: is_enabled() with warm local cache.

    Flag data already in cache — no Redis call needed.
    This is the hot path — called millions of times per day.
    Target: < 0.1ms per call.
    """
    # warm the cache
    flags.is_enabled("bench_flag", user_id="alice")

    result = benchmark(flags.is_enabled, "bench_flag", user_id="alice")
    assert isinstance(result, bool)


def test_is_enabled_cold_cache(benchmark, flags):
    """
    Benchmark: is_enabled() with cold cache — fetches from real Redis.

    Cache cleared before each call. Measures full Redis round-trip.
    Target: < 5ms per call.
    """
    def cold_call():
        flags._cache.clear()
        return flags.is_enabled("bench_flag", user_id="alice")

    result = benchmark(cold_call)
    assert isinstance(result, bool)


def test_is_enabled_user_allowlist(benchmark, flags):
    """
    Benchmark: is_enabled() for user in allowlist.

    Evaluates steps 1-4 — exits early at allowlist check.
    Target: similar to warm cache.
    """
    flags.is_enabled("allowlist_flag", user_id="alice")

    result = benchmark(flags.is_enabled, "allowlist_flag", user_id="alice")
    assert result is True


def test_is_enabled_cohort_match(benchmark, flags):
    """
    Benchmark: is_enabled() for user in cohort.

    Evaluates steps 1-5 — requires SINTER Redis call.
    Target: < 2ms per call with warm cache.
    """
    result = benchmark(flags.is_enabled, "cohort_flag", user_id="alice")
    assert result is True


def test_is_enabled_redis_down_stale_cache(benchmark, flags, redis_client):
    """
    Benchmark: is_enabled() when Redis is down — stale cache fallback.

    Simulates Redis outage. SDK serves last known state from memory.
    Target: < 0.1ms — same as warm cache (no Redis call).
    """
    # prime stale cache
    flags.is_enabled("bench_flag", user_id="alice")

    # simulate Redis down by using wrong port
    broken_client = redis.Redis(host=REDIS_HOST, port=9999)
    schema = SchemaKeys(env=ENV)
    stale_cache = LocalCache(ttl_seconds=1)

    # copy flag data to stale cache
    flag_key = schema.flag("bench_flag")
    data = redis_client.hgetall(flag_key)
    decoded = {k.decode(): v.decode() for k, v in data.items()}
    stale_cache.set(flag_key, decoded)

    # backdate cache to make it stale
    stale_cache._store[flag_key].cached_at = 0

    evaluator = Evaluator(broken_client, schema, stale_cache)

    result = benchmark(evaluator.is_enabled, "bench_flag", "alice", False)
    assert isinstance(result, bool)


def test_is_enabled_10k_flags(benchmark, flags):
    """
    Benchmark: is_enabled() with 10,000 flags in Redis.

    Tests that flag count does not degrade evaluation speed.
    Uses index Set — no KEYS * scan.
    Target: same speed as small flag count.
    """
    flags.is_enabled("flag_5000", user_id="alice")
    result = benchmark(flags.is_enabled, "flag_5000", user_id="alice")
    assert isinstance(result, bool)


def test_is_enabled_large_cohort_100k(benchmark, flags):
    """
    Benchmark: is_enabled() with 100,000 users in cohort.

    Tests SINTER performance with large cohort.
    Target: < 10ms — Redis SINTER is O(N*M) where N,M are set sizes.
    """
    result = benchmark(flags.is_enabled, "large_cohort_flag", user_id="user_50000")
    assert isinstance(result, bool)


def test_concurrent_100_threads(benchmark, flags):
    """
    Benchmark: 100 concurrent threads calling is_enabled() simultaneously.

    Tests thread safety and cache lock contention under load.
    Target: no errors, no race conditions.
    """
    errors = []

    def concurrent_eval():
        results = []
        for _ in range(100):
            try:
                result = flags.is_enabled("bench_flag", user_id="alice")
                results.append(result)
            except Exception as e:
                errors.append(e)
        return results

    def run_concurrent():
        threads = [threading.Thread(target=concurrent_eval) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    benchmark(run_concurrent)
    assert len(errors) == 0


def test_rollout_distribution_1000_users(benchmark, flags):
    """
    Benchmark: evaluate 1000 different users at rollout=50.

    Tests deterministic hashing speed across large user population.
    Verifies roughly 50% get True.
    Target: < 50ms for 1000 evaluations.
    """
    # warm cache
    flags.is_enabled("bench_flag", user_id="user_0")

    def eval_1000():
        results = [
            flags.is_enabled("bench_flag", user_id=f"user_{i}")
            for i in range(1000)
        ]
        return results

    results = benchmark(eval_1000)
    true_count = sum(results)
    assert 300 <= true_count <= 700, f"Expected ~500 true but got {true_count}"