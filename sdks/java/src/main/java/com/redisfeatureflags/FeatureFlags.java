package com.redisfeatureflags;

import com.redisfeatureflags.exceptions.FlagNotFoundError;
import com.redisfeatureflags.exceptions.InvalidRolloutError;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class FeatureFlags {

    private final JedisPool jedisPool;
    private final SchemaKeys schema;
    private final LocalCache cache;
    private final Evaluator evaluator;
    private final CohortManager cohorts;

    /**
     * Create FeatureFlags with existing JedisPool.
     */
    public FeatureFlags(JedisPool jedisPool, String env, int cacheTtlSeconds) {
        this.jedisPool = jedisPool;
        this.schema = new SchemaKeys(env);
        this.cache = new LocalCache(cacheTtlSeconds);
        this.evaluator = new Evaluator(jedisPool::getResource, schema, cache);
        this.cohorts = new CohortManager(jedisPool::getResource, schema);
    }

    public FeatureFlags(JedisPool jedisPool, String env) {
        this(jedisPool, env, 30);
    }

    /**
     * Create FeatureFlags with Redis URL.
     */
    public FeatureFlags(String redisUrl, String env) {
        this(new JedisPool(redisUrl), env, 30);
    }

    // ── Core evaluation ────────────────────────────────────────

    /**
     * Evaluate a flag for a user.
     *
     * @param flagName    Flag to evaluate
     * @param userId      User to evaluate for
     * @param defaultValue Return value if flag missing or Redis down
     * @return true if user should get the feature
     */
    public boolean isEnabled(String flagName, String userId, boolean defaultValue) {
        return evaluator.isEnabled(flagName, userId, defaultValue);
    }

    public boolean isEnabled(String flagName, String userId) {
        return evaluator.isEnabled(flagName, userId, false);
    }

    // ── Flag management ────────────────────────────────────────

    /**
     * Create a new flag — disabled by default.
     */
    public void create(String flagName, int rollout, String createdBy) {
        if (rollout < 0 || rollout > 100) {
            throw new InvalidRolloutError(rollout);
        }
        long ts = Utils.nowUnix();
        Map<String, String> fields = new HashMap<>();
        fields.put("enabled",      "0");
        fields.put("rollout",      String.valueOf(rollout));
        fields.put("expires_at",   "0");
        fields.put("created_at",   String.valueOf(ts));
        fields.put("updated_at",   String.valueOf(ts));
        fields.put("created_by",   createdBy);
        fields.put("updated_by",   createdBy);
        fields.put("flag_version", "1");

        try (Jedis jedis = jedisPool.getResource()) {
            jedis.hset(schema.flag(flagName), fields);
            jedis.sadd(schema.flagsIndex(), flagName);
        }
    }

    public void create(String flagName) {
        create(flagName, 0, "unknown");
    }

    public void create(String flagName, int rollout) {
        create(flagName, rollout, "unknown");
    }

    /**
     * Enable a flag.
     */
    public void enable(String flagName, String updatedBy) {
        assertExists(flagName);
        try (Jedis jedis = jedisPool.getResource()) {
            Map<String, String> fields = new HashMap<>();
            fields.put("enabled",    "1");
            fields.put("updated_at", String.valueOf(Utils.nowUnix()));
            fields.put("updated_by", updatedBy);
            jedis.hset(schema.flag(flagName), fields);
        }
        cache.delete(schema.flag(flagName));
    }

    public void enable(String flagName) {
        enable(flagName, "unknown");
    }

    /**
     * Disable a flag — instant kill switch.
     */
    public void disable(String flagName, String updatedBy) {
        assertExists(flagName);
        try (Jedis jedis = jedisPool.getResource()) {
            Map<String, String> fields = new HashMap<>();
            fields.put("enabled",    "0");
            fields.put("updated_at", String.valueOf(Utils.nowUnix()));
            fields.put("updated_by", updatedBy);
            jedis.hset(schema.flag(flagName), fields);
        }
        cache.delete(schema.flag(flagName));
    }

    public void disable(String flagName) {
        disable(flagName, "unknown");
    }

    /**
     * Update rollout percentage.
     */
    public void setRollout(String flagName, int percent, String updatedBy) {
        if (percent < 0 || percent > 100) {
            throw new InvalidRolloutError(percent);
        }
        assertExists(flagName);
        try (Jedis jedis = jedisPool.getResource()) {
            Map<String, String> fields = new HashMap<>();
            fields.put("rollout",    String.valueOf(percent));
            fields.put("updated_at", String.valueOf(Utils.nowUnix()));
            fields.put("updated_by", updatedBy);
            jedis.hset(schema.flag(flagName), fields);
        }
        cache.delete(schema.flag(flagName));
    }

    public void setRollout(String flagName, int percent) {
        setRollout(flagName, percent, "unknown");
    }

    /**
     * Delete a flag and all associated data.
     */
    public void delete(String flagName) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.del(schema.flag(flagName));
            jedis.del(schema.flagUsers(flagName));
            jedis.del(schema.flagCohorts(flagName));
            jedis.del(schema.flagHistory(flagName));
            jedis.srem(schema.flagsIndex(), flagName);
        }
        cache.delete(schema.flag(flagName));
    }

    /**
     * Get all flag fields.
     */
    public Map<String, String> get(String flagName) {
        assertExists(flagName);
        try (Jedis jedis = jedisPool.getResource()) {
            return jedis.hgetAll(schema.flag(flagName));
        }
    }

    /**
     * List all flag names — sorted.
     */
    public List<String> listFlags() {
        try (Jedis jedis = jedisPool.getResource()) {
            return jedis.smembers(schema.flagsIndex())
                    .stream()
                    .sorted()
                    .collect(java.util.stream.Collectors.toList());
        }
    }

    // ── User targeting ─────────────────────────────────────────

    public void addUser(String flagName, String userId) {
        assertExists(flagName);
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.sadd(schema.flagUsers(flagName), userId);
        }
    }

    public void removeUser(String flagName, String userId) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.srem(schema.flagUsers(flagName), userId);
        }
    }

    // ── Cohort targeting ───────────────────────────────────────

    public void createCohort(String cohortName) {
        cohorts.create(cohortName);
    }

    public void deleteCohort(String cohortName) {
        cohorts.delete(cohortName);
    }

    public void addToCohort(String cohortName, String userId) {
        cohorts.addUser(cohortName, userId);
    }

    public void removeFromCohort(String cohortName, String userId) {
        cohorts.removeUser(cohortName, userId);
    }

    public void addCohortToFlag(String flagName, String cohortName) {
        assertExists(flagName);
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.sadd(schema.flagCohorts(flagName), cohortName);
        }
    }

    public void removeCohortFromFlag(String flagName, String cohortName) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.srem(schema.flagCohorts(flagName), cohortName);
        }
    }

    public List<String> listCohorts() {
        return cohorts.listCohorts();
    }

    public Set<String> getCohortMembers(String cohortName) {
        return cohorts.getMembers(cohortName);
    }

    // ── Private helpers ────────────────────────────────────────

    private void assertExists(String flagName) {
        try (Jedis jedis = jedisPool.getResource()) {
            if (!jedis.exists(schema.flag(flagName))) {
                throw new FlagNotFoundError(flagName);
            }
        }
    }
}