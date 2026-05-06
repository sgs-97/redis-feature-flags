package com.redisfeatureflags;

import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import java.util.Map;
import java.util.Set;

public class Evaluator {

    private final JedisProvider jedisProvider;
    private final SchemaKeys schema;
    private final LocalCache cache;

    public Evaluator(JedisProvider jedisProvider, SchemaKeys schema, LocalCache cache) {
        this.jedisProvider = jedisProvider;
        this.schema = schema;
        this.cache = cache;
    }

    /**
     * Evaluate a flag for a user.
     * 6 steps — short-circuits at first answer.
     */
    public boolean isEnabled(String flagName, String userId, boolean defaultValue) {

        // Step 1 — load flag data
        Map<String, String> flagData = loadFlag(schema.flag(flagName));
        if (flagData == null || flagData.isEmpty()) return defaultValue;

        // Step 2 — kill switch
        if (!"1".equals(flagData.get("enabled"))) return false;

        // Step 3 — expiry
        long expiresAt = parseLong(flagData.get("expires_at"), 0L);
        if (Utils.isExpired(expiresAt)) return false;

        // Step 4 — user allowlist
        if (userInAllowlist(flagName, userId)) return true;

        // Step 5 — cohort
        if (userInCohort(flagName, userId)) return true;

        // Step 6 — rollout
        int rollout = parseInt(flagData.get("rollout"), 0);
        return Utils.evaluateRollout(flagName, userId, rollout);
    }

    // ── Private helpers ────────────────────────────────────────

    private Map<String, String> loadFlag(String flagKey) {
        // 1. fresh cache
        Map<String, String> cached = cache.get(flagKey);
        if (cached != null) return cached;

        // 2. Redis
        try (Jedis jedis = jedisProvider.getResource()) {
            Map<String, String> data = jedis.hgetAll(flagKey);
            if (data == null || data.isEmpty()) return null;
            cache.set(flagKey, data);
            return data;
        } catch (Exception e) {
            // 3. stale cache fallback
            return cache.getStale(flagKey);
        }
    }

    private boolean userInAllowlist(String flagName, String userId) {
        try (Jedis jedis = jedisProvider.getResource()) {
            return jedis.sismember(schema.flagUsers(flagName), userId);
        } catch (Exception e) {
            return false;
        }
    }

    private boolean userInCohort(String flagName, String userId) {
        try (Jedis jedis = jedisProvider.getResource()) {
            Set<String> intersection = jedis.sinter(
                schema.userCohorts(userId),
                schema.flagCohorts(flagName)
            );
            return !intersection.isEmpty();
        } catch (Exception e) {
            return false;
        }
    }

    private long parseLong(String value, long defaultVal) {
        if (value == null || value.isEmpty()) return defaultVal;
        try { return Long.parseLong(value); }
        catch (NumberFormatException e) { return defaultVal; }
    }

    private int parseInt(String value, int defaultVal) {
        if (value == null || value.isEmpty()) return defaultVal;
        try { return Integer.parseInt(value); }
        catch (NumberFormatException e) { return defaultVal; }
    }
}