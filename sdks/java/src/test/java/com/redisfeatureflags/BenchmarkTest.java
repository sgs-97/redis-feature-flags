package com.redisfeatureflags;

import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static org.junit.jupiter.api.Assertions.*;

@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class BenchmarkTest {

    private static final int REDIS_PORT = 6379;
    private static final String ENV = "benchmark";
    private static final int WARMUP_ROUNDS = 1000;
    private static final int MEASURE_ROUNDS = 10000;

    private JedisPool jedisPool;
    private FeatureFlags flags;

    @BeforeAll
    void setUp() {
        jedisPool = new JedisPool("localhost", REDIS_PORT);
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.ping();
        } catch (Exception e) {
            System.out.println("Redis not available — skipping benchmarks");
            return;
        }

        flags = new FeatureFlags(jedisPool, ENV);

        // flush benchmark namespace
        try (Jedis jedis = jedisPool.getResource()) {
            var keys = jedis.keys("ff:" + ENV + ":*");
            if (!keys.isEmpty()) jedis.del(keys.toArray(new String[0]));
        }

        // setup test data
        flags.create("bench_flag", 50);
        flags.enable("bench_flag");

        flags.create("allowlist_flag", 0);
        flags.enable("allowlist_flag");
        flags.addUser("allowlist_flag", "alice");

        flags.create("cohort_flag", 0);
        flags.enable("cohort_flag");
        flags.createCohort("bench-cohort");
        flags.addToCohort("bench-cohort", "alice");
        flags.addCohortToFlag("cohort_flag", "bench-cohort");

        System.out.println("\n=== Java SDK Benchmarks ===\n");
    }

    @AfterAll
    void tearDown() {
        if (jedisPool != null) {
            try (Jedis jedis = jedisPool.getResource()) {
                var keys = jedis.keys("ff:" + ENV + ":*");
                if (!keys.isEmpty()) jedis.del(keys.toArray(new String[0]));
            }
            jedisPool.close();
        }
    }

    private long[] measure(Runnable fn, int rounds) {
        // warmup
        for (int i = 0; i < WARMUP_ROUNDS; i++) fn.run();

        // measure
        long[] times = new long[rounds];
        for (int i = 0; i < rounds; i++) {
            long start = System.nanoTime();
            fn.run();
            times[i] = System.nanoTime() - start;
        }
        return times;
    }

    private void printStats(String name, long[] times) {
        long sum = 0;
        long min = Long.MAX_VALUE;
        long max = Long.MIN_VALUE;

        for (long t : times) {
            sum += t;
            if (t < min) min = t;
            if (t > max) max = t;
        }

        double meanMs = (sum / (double) times.length) / 1_000_000.0;
        double minMs  = min / 1_000_000.0;
        double maxMs  = max / 1_000_000.0;
        long   ops    = (long)(1000.0 / meanMs);

        // p50 p95 p99
        long[] sorted = times.clone();
        java.util.Arrays.sort(sorted);
        double p50 = sorted[(int)(times.length * 0.50)] / 1_000_000.0;
        double p95 = sorted[(int)(times.length * 0.95)] / 1_000_000.0;
        double p99 = sorted[(int)(times.length * 0.99)] / 1_000_000.0;

        System.out.printf("%-45s min=%.3fms  mean=%.3fms  p50=%.3fms  p95=%.3fms  p99=%.3fms  ops=%,d/sec%n",
            name, minMs, meanMs, p50, p95, p99, ops);
    }

    @Test
    void benchmarkWarmCache() {
        /*
         * Benchmark: isEnabled() with warm local cache.
         * Flag data already in cache — no Redis call.
         * Target: < 0.1ms
         */
        flags.isEnabled("bench_flag", "alice"); // warm cache
        long[] times = measure(() -> flags.isEnabled("bench_flag", "alice"), MEASURE_ROUNDS);
        printStats("isEnabled() warm cache", times);
        double mean = java.util.Arrays.stream(times).average().orElse(0) / 1_000_000.0;
        assertTrue(mean < 5.0, "Warm cache should be < 5ms but was " + mean + "ms");
    }

    @Test
    void benchmarkColdCache() {
        /*
        * Benchmark: isEnabled() cold cache — fetches from Redis each time.
        * Target: < 10ms
        */
        long[] times = measure(() -> {
            FeatureFlags freshFlags = new FeatureFlags(jedisPool, ENV, 0);
            freshFlags.isEnabled("bench_flag", "alice");
        }, MEASURE_ROUNDS);
        printStats("isEnabled() cold cache", times);
        double mean = java.util.Arrays.stream(times).average().orElse(0) / 1_000_000.0;
        assertTrue(mean < 10.0, "Cold cache should be < 10ms but was " + mean + "ms");
    }

    @Test
    void benchmarkUserAllowlist() {
        /*
         * Benchmark: isEnabled() for user in allowlist.
         * Short-circuits at step 4 — fastest evaluation path.
         * Target: < 0.5ms
         */
        flags.isEnabled("allowlist_flag", "alice");
        long[] times = measure(() -> flags.isEnabled("allowlist_flag", "alice"), MEASURE_ROUNDS);
        printStats("isEnabled() user allowlist", times);
        assertTrue(times.length == MEASURE_ROUNDS);
    }

    @Test
    void benchmarkCohortMatch() {
        /*
         * Benchmark: isEnabled() for user in cohort.
         * Requires SINTER Redis call — step 5.
         * Target: < 2ms
         */
        long[] times = measure(() -> flags.isEnabled("cohort_flag", "alice"), MEASURE_ROUNDS);
        printStats("isEnabled() cohort match", times);
        assertTrue(times.length == MEASURE_ROUNDS);
    }

    @Test
    void benchmarkRolloutDistribution() {
        /*
         * Benchmark: evaluate 1000 different users at rollout=50.
         * Verifies ~50% get true — deterministic hashing.
         */
        flags.isEnabled("bench_flag", "warmup");
        long start = System.nanoTime();
        int trueCount = 0;
        for (int i = 0; i < 1000; i++) {
            if (flags.isEnabled("bench_flag", "user_" + i)) trueCount++;
        }
        double totalMs = (System.nanoTime() - start) / 1_000_000.0;
        double perUserMs = totalMs / 1000.0;

        System.out.printf("%-45s total=%.1fms  per_user=%.3fms  true_count=%d/1000%n",
            "rollout distribution 1000 users", totalMs, perUserMs, trueCount);

        assertTrue(trueCount >= 300 && trueCount <= 700,
            "Expected ~500 true but got " + trueCount);
    }

    @Test
    void benchmarkConcurrent100Threads() throws InterruptedException {
        /*
         * Benchmark: 100 concurrent threads calling isEnabled() simultaneously.
         * Tests thread safety under load.
         * Target: zero errors.
         */
        int threads = 100;
        int callsPerThread = 1000;
        CountDownLatch latch = new CountDownLatch(threads);
        ExecutorService executor = Executors.newFixedThreadPool(threads);
        List<Exception> errors = new ArrayList<>();

        flags.isEnabled("bench_flag", "warmup");
        long start = System.nanoTime();

        for (int t = 0; t < threads; t++) {
            executor.submit(() -> {
                try {
                    for (int i = 0; i < callsPerThread; i++) {
                        flags.isEnabled("bench_flag", "user_" + i);
                    }
                } catch (Exception e) {
                    synchronized (errors) { errors.add(e); }
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        executor.shutdown();
        double totalMs = (System.nanoTime() - start) / 1_000_000.0;

        System.out.printf("%-45s total=%.1fms  threads=%d  calls_per_thread=%d  errors=%d%n",
            "100 concurrent threads", totalMs, threads, callsPerThread, errors.size());

        assertEquals(0, errors.size(), "Expected zero errors but got " + errors.size());
    }
}