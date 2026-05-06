package com.redisfeatureflags.unit;

import com.redisfeatureflags.*;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static org.junit.jupiter.api.Assertions.*;

class LocalCacheTest {

    private LocalCache cache;

    @BeforeEach
    void setUp() {
        cache = new LocalCache(30);
    }

    // ── get ────────────────────────────────────────────────────

    @Test
    void getReturnsNullWhenEmpty() {
        /*
         * Given: empty cache.
         * Expected: get() returns null — key does not exist.
         */
        assertNull(cache.get("ff:prod:flag:dark_mode"));
    }

    @Test
    void setAndGet() {
        /*
         * Given: flag stored in cache.
         * Expected: get() returns exact same data.
         */
        Map<String, String> data = Map.of("enabled", "1", "rollout", "10");
        cache.set("ff:prod:flag:dark_mode", data);
        assertEquals(data, cache.get("ff:prod:flag:dark_mode"));
    }

    @Test
    void getReturnsNullAfterTtlExpiry() throws InterruptedException {
        /*
         * Given: cache with TTL=1 second. Entry stored.
         * After: 2 seconds pass.
         * Expected: get() returns null — entry expired.
         */
        cache = new LocalCache(1);
        cache.set("ff:prod:flag:dark_mode", Map.of("enabled", "1"));
        Thread.sleep(1100);
        assertNull(cache.get("ff:prod:flag:dark_mode"));
    }

    // ── getStale ───────────────────────────────────────────────

    @Test
    void getStaleReturnsExpiredData() throws InterruptedException {
        /*
         * Given: cache with TTL=1 second. Entry stored. TTL passed.
         * Expected: get() returns null but getStale() returns data.
         *           Stale cache used as fallback when Redis is down.
         */
        cache = new LocalCache(1);
        Map<String, String> data = Map.of("enabled", "1");
        cache.set("ff:prod:flag:dark_mode", data);
        Thread.sleep(1100);
        assertNull(cache.get("ff:prod:flag:dark_mode"));
        assertEquals(data, cache.getStale("ff:prod:flag:dark_mode"));
    }

    @Test
    void getStaleReturnsNullWhenNeverCached() {
        /*
         * Given: empty cache — flag never stored.
         * Expected: getStale() returns null — nothing to serve.
         */
        assertNull(cache.getStale("ff:prod:flag:nonexistent"));
    }

    // ── delete ─────────────────────────────────────────────────

    @Test
    void deleteRemovesEntry() {
        /*
         * Given: flag stored in cache.
         * After: delete() called.
         * Expected: get() returns null — entry gone.
         */
        cache.set("ff:prod:flag:dark_mode", Map.of("enabled", "1"));
        cache.delete("ff:prod:flag:dark_mode");
        assertNull(cache.get("ff:prod:flag:dark_mode"));
    }

    @Test
    void deleteNonexistentKeyNoError() {
        /*
         * Given: empty cache.
         * After: delete() called on missing key.
         * Expected: no exception — safe to delete missing keys.
         */
        assertDoesNotThrow(() -> cache.delete("ff:prod:flag:nonexistent"));
    }

    @Test
    void deleteRemovesStaleEntryToo() throws InterruptedException {
        /*
         * Given: expired entry in cache.
         * After: delete() called.
         * Expected: getStale() also returns null — fully removed.
         */
        cache = new LocalCache(1);
        cache.set("ff:prod:flag:dark_mode", Map.of("enabled", "1"));
        Thread.sleep(1100);
        cache.delete("ff:prod:flag:dark_mode");
        assertNull(cache.getStale("ff:prod:flag:dark_mode"));
    }

    // ── clear ──────────────────────────────────────────────────

    @Test
    void clearRemovesAllEntries() {
        /*
         * Given: two flags stored in cache.
         * After: clear() called.
         * Expected: size is 0 — all entries removed.
         */
        cache.set("ff:prod:flag:dark_mode",    Map.of("enabled", "1"));
        cache.set("ff:prod:flag:new_checkout", Map.of("enabled", "0"));
        cache.clear();
        assertEquals(0, cache.size());
    }

    // ── size ───────────────────────────────────────────────────

    @Test
    void sizeReflectsEntryCount() {
        /*
         * Given: flags added and deleted one by one.
         * Expected: size() reflects exact count at each step.
         */
        assertEquals(0, cache.size());
        cache.set("ff:prod:flag:dark_mode", Map.of("enabled", "1"));
        assertEquals(1, cache.size());
        cache.set("ff:prod:flag:new_checkout", Map.of("enabled", "0"));
        assertEquals(2, cache.size());
        cache.delete("ff:prod:flag:dark_mode");
        assertEquals(1, cache.size());
    }

    // ── thread safety ──────────────────────────────────────────

    @Test
    void concurrentWritesNoCorruption() throws InterruptedException {
        /*
         * Given: 10 threads each writing 100 flags simultaneously.
         * Expected: no exceptions — ConcurrentHashMap prevents corruption.
         */
        int threads = 10;
        CountDownLatch latch = new CountDownLatch(threads);
        ExecutorService executor = Executors.newFixedThreadPool(threads);

        for (int t = 0; t < threads; t++) {
            final int threadId = t;
            executor.submit(() -> {
                try {
                    for (int i = 0; i < 100; i++) {
                        cache.set(
                            "ff:prod:flag:flag_" + threadId + "_" + i,
                            Map.of("enabled", "1")
                        );
                    }
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        executor.shutdown();
        assertEquals(1000, cache.size());
    }

    @Test
    void concurrentReadsAndWritesNoError() throws InterruptedException {
        /*
         * Given: 5 threads reading and 5 threads writing same key simultaneously.
         * Expected: no exceptions — reads and writes do not corrupt each other.
         */
        cache.set("ff:prod:flag:dark_mode", Map.of("enabled", "1"));

        int threads = 10;
        CountDownLatch latch = new CountDownLatch(threads);
        ExecutorService executor = Executors.newFixedThreadPool(threads);
        boolean[] errors = {false};

        for (int t = 0; t < threads; t++) {
            final boolean isWriter = t < 5;
            executor.submit(() -> {
                try {
                    for (int i = 0; i < 100; i++) {
                        if (isWriter) {
                            cache.set("ff:prod:flag:dark_mode",
                                Map.of("enabled", "1", "rollout", String.valueOf(i)));
                        } else {
                            cache.get("ff:prod:flag:dark_mode");
                        }
                    }
                } catch (Exception e) {
                    errors[0] = true;
                } finally {
                    latch.countDown();
                }
            });
        }

        latch.await();
        executor.shutdown();
        assertFalse(errors[0]);
    }
}