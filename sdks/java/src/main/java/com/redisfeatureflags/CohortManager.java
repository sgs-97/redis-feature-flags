package com.redisfeatureflags;

import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.Pipeline;

import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

public class CohortManager {

    private final JedisProvider jedisProvider;
    private final SchemaKeys schema;

    public CohortManager(JedisProvider jedisProvider, SchemaKeys schema) {
        this.jedisProvider = jedisProvider;
        this.schema = schema;
    }

    /**
     * Register cohort name in index.
     * Actual Set created lazily on first addUser().
     */
    public void create(String cohortName) {
        try (Jedis jedis = jedisProvider.getResource()) {
            jedis.sadd(schema.cohortsIndex(), cohortName);
        }
    }

    /**
     * Delete cohort — cleans members Set, reverse index, and cohorts index.
     */
    public void delete(String cohortName) {
        try (Jedis jedis = jedisProvider.getResource()) {
            // get all members before deleting
            Set<String> members = jedis.smembers(schema.cohort(cohortName));

            Pipeline pipe = jedis.pipelined();

            // clean reverse index for every member
            for (String member : members) {
                pipe.srem(schema.userCohorts(member), cohortName);
            }

            // delete cohort Set and remove from index
            pipe.del(schema.cohort(cohortName));
            pipe.srem(schema.cohortsIndex(), cohortName);
            pipe.sync();
        }
    }

    /**
     * Add user to cohort — writes both directions atomically.
     * Direction 1: cohort → members
     * Direction 2: user → cohorts (reverse index)
     */
    public void addUser(String cohortName, String userId) {
        try (Jedis jedis = jedisProvider.getResource()) {
            Pipeline pipe = jedis.pipelined();
            pipe.sadd(schema.cohort(cohortName), userId);
            pipe.sadd(schema.userCohorts(userId), cohortName);
            pipe.sync();
        }
    }

    /**
     * Remove user from cohort — removes both directions atomically.
     */
    public void removeUser(String cohortName, String userId) {
        try (Jedis jedis = jedisProvider.getResource()) {
            Pipeline pipe = jedis.pipelined();
            pipe.srem(schema.cohort(cohortName), userId);
            pipe.srem(schema.userCohorts(userId), cohortName);
            pipe.sync();
        }
    }

    /**
     * Get all members of a cohort.
     */
    public Set<String> getMembers(String cohortName) {
        try (Jedis jedis = jedisProvider.getResource()) {
            return jedis.smembers(schema.cohort(cohortName));
        }
    }

    /**
     * List all cohort names from index.
     */
    public List<String> listCohorts() {
        try (Jedis jedis = jedisProvider.getResource()) {
            return jedis.smembers(schema.cohortsIndex())
                    .stream()
                    .sorted()
                    .collect(Collectors.toList());
        }
    }

    /**
     * Check if cohort exists in index.
     */
    public boolean exists(String cohortName) {
        try (Jedis jedis = jedisProvider.getResource()) {
            return jedis.sismember(schema.cohortsIndex(), cohortName);
        }
    }
}