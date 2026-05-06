package com.redisfeatureflags.e2e;

import com.redisfeatureflags.*;

import com.redisfeatureflags.exceptions.InvalidRolloutError;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class EvaluatorTest {

    private JedisPool jedisPool;
    private SchemaKeys schema;
    private LocalCache cache;
    private Evaluator evaluator;

    @BeforeEach
    void setUp() {
        jedisPool = new JedisPool("localhost", 6379);
        schema = new SchemaKeys("test");
        cache = new LocalCache(30);
        evaluator = new Evaluator(jedisPool::getResource, schema, cache);
    }

    @AfterEach
    void tearDown() {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.flushAll();
        }
        jedisPool.close();
    }

    // ── helpers ────────────────────────────────────────────────

    private void createFlag(String flagName, String enabled, int rollout) {
        try (var jedis = jedisPool.getResource()) {
            Map<String, String> fields = new HashMap<>();
            fields.put("enabled",    enabled);
            fields.put("rollout",    String.valueOf(rollout));
            fields.put("expires_at", "0");
            fields.put("flag_version", "1");
            jedis.hset(schema.flag(flagName), fields);
        }
    }

    // ── missing flag ───────────────────────────────────────────

    @Test
    void missingFlagReturnsDefaultFalse() {
        /*
         * Given: flag does not exist in Redis.
         * Expected: isEnabled() returns false — the default.
         */
        assertFalse(evaluator.isEnabled("nonexistent", "alice", false));
    }

    @Test
    void missingFlagReturnsCustomDefault() {
        /*
         * Given: flag does not exist in Redis.
         * Expected: isEnabled() returns true — custom default passed by caller.
         */
        assertTrue(evaluator.isEnabled("nonexistent", "alice", true));
    }

    // ── kill switch ────────────────────────────────────────────

    @Test
    void disabledFlagReturnsFalse() {
        /*
         * Given: flag with enabled=0, rollout=100.
         * Expected: false — kill switch overrides everything.
         */
        createFlag("dark_mode", "0", 100);
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void enabledFlagZeroRolloutReturnsFalse() {
        /*
         * Given: flag with enabled=1, rollout=0.
         * Expected: false — nobody in a 0% rollout.
         */
        createFlag("dark_mode", "1", 0);
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── expiry ─────────────────────────────────────────────────

    @Test
    void expiredFlagReturnsFalse() {
        /*
         * Given: flag with expires_at=1000 (year 1970 — definitely past).
         * Expected: false — flag has expired.
         */
        try (var jedis = jedisPool.getResource()) {
            Map<String, String> fields = new HashMap<>();
            fields.put("enabled",    "1");
            fields.put("rollout",    "100");
            fields.put("expires_at", "1000");
            fields.put("flag_version", "1");
            jedis.hset(schema.flag("dark_mode"), fields);
        }
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void futureExpiryDoesNotBlock() {
        /*
         * Given: flag with expires_at 24 hours in future.
         * Expected: true — flag has not expired yet.
         */
        try (var jedis = jedisPool.getResource()) {
            Map<String, String> fields = new HashMap<>();
            fields.put("enabled",    "1");
            fields.put("rollout",    "100");
            fields.put("expires_at", String.valueOf(Utils.nowUnix() + 86400));
            fields.put("flag_version", "1");
            jedis.hset(schema.flag("dark_mode"), fields);
        }
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void zeroExpiryNeverExpires() {
        /*
         * Given: flag with expires_at=0 — never expires.
         * Expected: true — flag runs forever.
         */
        createFlag("dark_mode", "1", 100);
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── user allowlist ─────────────────────────────────────────

    @Test
    void userInAllowlistReturnsTrue() {
        /*
         * Given: flag with rollout=0. Alice in user allowlist.
         * Expected: true — allowlist overrides rollout.
         */
        createFlag("dark_mode", "1", 0);
        try (var jedis = jedisPool.getResource()) {
            jedis.sadd(schema.flagUsers("dark_mode"), "alice");
        }
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void userNotInAllowlistContinuesToRollout() {
        /*
         * Given: flag with rollout=0. Bob in allowlist but not Alice.
         * Expected: false for Alice — not in allowlist, rollout is 0.
         */
        createFlag("dark_mode", "1", 0);
        try (var jedis = jedisPool.getResource()) {
            jedis.sadd(schema.flagUsers("dark_mode"), "bob");
        }
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── cohorts ────────────────────────────────────────────────

    @Test
    void userInCohortReturnsTrue() {
        /*
         * Given: flag allows beta-testers. Alice in beta-testers.
         * Expected: true — cohort match found.
         */
        createFlag("dark_mode", "1", 0);
        try (var jedis = jedisPool.getResource()) {
            jedis.sadd(schema.flagCohorts("dark_mode"), "beta-testers");
            jedis.sadd(schema.userCohorts("alice"), "beta-testers");
        }
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void userNotInCohortReturnsFalse() {
        /*
         * Given: flag allows beta-testers. Alice in premium-users only.
         * Expected: false — no cohort match.
         */
        createFlag("dark_mode", "1", 0);
        try (var jedis = jedisPool.getResource()) {
            jedis.sadd(schema.flagCohorts("dark_mode"), "beta-testers");
            jedis.sadd(schema.userCohorts("alice"), "premium-users");
        }
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── rollout ────────────────────────────────────────────────

    @Test
    void rollout100ReturnsTrue() {
        /*
         * Given: flag with rollout=100.
         * Expected: true — everyone gets it.
         */
        createFlag("dark_mode", "1", 100);
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void rollout0ReturnsFalse() {
        /*
         * Given: flag with rollout=0.
         * Expected: false — nobody gets it.
         */
        createFlag("dark_mode", "1", 0);
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void rolloutDeterministic() {
        /*
         * Given: same flag, same user, rollout=50 — evaluated twice.
         * Expected: both calls return same result — deterministic hashing.
         */
        createFlag("dark_mode", "1", 50);
        boolean r1 = evaluator.isEnabled("dark_mode", "alice", false);
        boolean r2 = evaluator.isEnabled("dark_mode", "alice", false);
        assertEquals(r1, r2);
    }

    // ── cache ──────────────────────────────────────────────────

    @Test
    void resultServedFromCacheOnSecondCall() {
        /*
         * Given: flag evaluated once — populates local cache.
         *        Flag then deleted from Redis.
         * Expected: second call still returns true — served from cache.
         */
        createFlag("dark_mode", "1", 100);
        evaluator.isEnabled("dark_mode", "alice", false);

        try (var jedis = jedisPool.getResource()) {
            jedis.del(schema.flag("dark_mode"));
        }

        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── priority order ─────────────────────────────────────────

    @Test
    void allowlistTakesPriorityOverRollout() {
        /*
         * Given: rollout=0 — would return false. Alice in allowlist.
         * Expected: true — allowlist checked before rollout.
         */
        createFlag("dark_mode", "1", 0);
        try (var jedis = jedisPool.getResource()) {
            jedis.sadd(schema.flagUsers("dark_mode"), "alice");
        }
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void disabledOverridesAllowlist() {
        /*
         * Given: flag disabled. Alice in allowlist. Rollout=100.
         * Expected: false — kill switch checked first, overrides everything.
         */
        createFlag("dark_mode", "0", 100);
        try (var jedis = jedisPool.getResource()) {
            jedis.sadd(schema.flagUsers("dark_mode"), "alice");
        }
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }
}