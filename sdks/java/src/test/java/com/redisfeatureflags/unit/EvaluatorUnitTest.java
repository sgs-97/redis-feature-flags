// src/test/java/com/redisfeatureflags/unit/EvaluatorUnitTest.java
package com.redisfeatureflags.unit;

import com.redisfeatureflags.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;

class EvaluatorUnitTest {

    @Mock JedisProvider jedisProvider;
    @Mock Jedis jedis;

    private SchemaKeys schema;
    private LocalCache cache;
    private Evaluator evaluator;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        when(jedisProvider.getResource()).thenReturn(jedis);
        schema = new SchemaKeys("test");
        cache = new LocalCache(30);
        evaluator = new Evaluator(jedisProvider, schema, cache);
    }

    private Map<String, String> flagData(String enabled, int rollout) {
        Map<String, String> data = new HashMap<>();
        data.put("enabled",      enabled);
        data.put("rollout",      String.valueOf(rollout));
        data.put("expires_at",   "0");
        data.put("flag_version", "1");
        return data;
    }

    // ── missing flag ───────────────────────────────────────────

    @Test
    void missingFlagReturnsDefaultFalse() {
        /*
         * Given: Redis returns empty map — flag does not exist.
         * Expected: isEnabled() returns false — the default.
         */
        when(jedis.hgetAll(schema.flag("dark_mode"))).thenReturn(Map.of());
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void missingFlagReturnsCustomDefault() {
        /*
         * Given: Redis returns empty map — flag does not exist.
         * Expected: isEnabled() returns true — custom default passed by caller.
         */
        when(jedis.hgetAll(schema.flag("dark_mode"))).thenReturn(Map.of());
        assertTrue(evaluator.isEnabled("dark_mode", "alice", true));
    }

    // ── kill switch ────────────────────────────────────────────

    @Test
    void disabledFlagReturnsFalse() {
        /*
         * Given: flag with enabled=0, rollout=100.
         * Expected: false — kill switch overrides everything.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenReturn(flagData("0", 100));
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void enabledFlagZeroRolloutReturnsFalse() {
        /*
         * Given: flag with enabled=1, rollout=0. User not in allowlist or cohort.
         * Expected: false — nobody in 0% rollout.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenReturn(flagData("1", 0));
        when(jedis.sismember(schema.flagUsers("dark_mode"), "alice"))
            .thenReturn(false);
        when(jedis.sinter(schema.userCohorts("alice"), schema.flagCohorts("dark_mode")))
            .thenReturn(Set.of());
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── expiry ─────────────────────────────────────────────────

    @Test
    void expiredFlagReturnsFalse() {
        /*
         * Given: flag with expires_at=1000 (year 1970 — definitely past).
         * Expected: false — flag has expired.
         */
        Map<String, String> data = flagData("1", 100);
        data.put("expires_at", "1000");
        when(jedis.hgetAll(schema.flag("dark_mode"))).thenReturn(data);
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void futureExpiryDoesNotBlock() {
        /*
         * Given: flag with expires_at 24 hours in future.
         * Expected: true — flag has not expired yet.
         */
        Map<String, String> data = flagData("1", 100);
        data.put("expires_at", String.valueOf(Utils.nowUnix() + 86400));
        when(jedis.hgetAll(schema.flag("dark_mode"))).thenReturn(data);
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── user allowlist ─────────────────────────────────────────

    @Test
    void userInAllowlistReturnsTrue() {
        /*
         * Given: flag with rollout=0. Alice in user allowlist.
         * Expected: true — allowlist overrides rollout.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenReturn(flagData("1", 0));
        when(jedis.sismember(schema.flagUsers("dark_mode"), "alice"))
            .thenReturn(true);
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void userNotInAllowlistContinuesToRollout() {
        /*
         * Given: flag with rollout=0. Alice not in allowlist or cohort.
         * Expected: false — not in allowlist, rollout is 0.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenReturn(flagData("1", 0));
        when(jedis.sismember(schema.flagUsers("dark_mode"), "alice"))
            .thenReturn(false);
        when(jedis.sinter(schema.userCohorts("alice"), schema.flagCohorts("dark_mode")))
            .thenReturn(Set.of());
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── cohorts ────────────────────────────────────────────────

    @Test
    void userInCohortReturnsTrue() {
        /*
         * Given: flag with rollout=0. Alice not in allowlist.
         *        SINTER returns beta-testers — cohort match found.
         * Expected: true.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenReturn(flagData("1", 0));
        when(jedis.sismember(schema.flagUsers("dark_mode"), "alice"))
            .thenReturn(false);
        when(jedis.sinter(schema.userCohorts("alice"), schema.flagCohorts("dark_mode")))
            .thenReturn(Set.of("beta-testers"));
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void userNotInCohortReturnsFalse() {
        /*
         * Given: flag with rollout=0. Alice not in allowlist.
         *        SINTER returns empty — no cohort match.
         * Expected: false.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenReturn(flagData("1", 0));
        when(jedis.sismember(schema.flagUsers("dark_mode"), "alice"))
            .thenReturn(false);
        when(jedis.sinter(schema.userCohorts("alice"), schema.flagCohorts("dark_mode")))
            .thenReturn(Set.of());
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── rollout ────────────────────────────────────────────────

    @Test
    void rollout100ReturnsTrue() {
        /*
         * Given: flag with rollout=100. Alice not in allowlist or cohort.
         * Expected: true — everyone in 100% rollout.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenReturn(flagData("1", 100));
        when(jedis.sismember(schema.flagUsers("dark_mode"), "alice"))
            .thenReturn(false);
        when(jedis.sinter(schema.userCohorts("alice"), schema.flagCohorts("dark_mode")))
            .thenReturn(Set.of());
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── cache ──────────────────────────────────────────────────

    @Test
    void resultServedFromCacheOnSecondCall() {
        /*
         * Given: flag fetched once — cached. Redis returns empty on second call.
         * Expected: second call returns true — served from cache.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenReturn(flagData("1", 100))
            .thenReturn(Map.of());
        when(jedis.sismember(anyString(), anyString())).thenReturn(false);
        when(jedis.sinter(anyString(), anyString())).thenReturn(Set.of());

        evaluator.isEnabled("dark_mode", "alice", false);
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
        verify(jedis, times(1)).hgetAll(schema.flag("dark_mode"));
    }

    // ── Redis down ─────────────────────────────────────────────

    @Test
    void redisDownReturnsStaleCacheIfAvailable() {
        /*
         * Given: flag in stale cache. Redis throws exception.
         * Expected: stale cache served — application keeps working.
         */
        cache.set(schema.flag("dark_mode"), flagData("1", 100));
        // backdate to make stale
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenThrow(new RuntimeException("Redis down"));
        when(jedis.sismember(anyString(), anyString())).thenReturn(false);
        when(jedis.sinter(anyString(), anyString())).thenReturn(Set.of());
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void redisDownNoCacheReturnsDefault() {
        /*
         * Given: empty cache. Redis throws exception.
         * Expected: default value returned — false.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenThrow(new RuntimeException("Redis down"));
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
    }

    // ── priority order ─────────────────────────────────────────

    @Test
    void allowlistTakesPriorityOverRollout() {
        /*
         * Given: rollout=0 — would return false. Alice in allowlist.
         * Expected: true — allowlist checked before rollout.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenReturn(flagData("1", 0));
        when(jedis.sismember(schema.flagUsers("dark_mode"), "alice"))
            .thenReturn(true);
        assertTrue(evaluator.isEnabled("dark_mode", "alice", false));
    }

    @Test
    void disabledOverridesAllowlist() {
        /*
         * Given: flag disabled. Alice in allowlist. Rollout=100.
         * Expected: false — kill switch checked first, overrides everything.
         */
        when(jedis.hgetAll(schema.flag("dark_mode")))
            .thenReturn(flagData("0", 100));
        assertFalse(evaluator.isEnabled("dark_mode", "alice", false));
        verify(jedis, never()).sismember(anyString(), anyString());
    }
}