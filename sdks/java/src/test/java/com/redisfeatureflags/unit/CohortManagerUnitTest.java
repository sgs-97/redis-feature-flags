// src/test/java/com/redisfeatureflags/unit/CohortManagerUnitTest.java
package com.redisfeatureflags.unit;

import com.redisfeatureflags.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.Pipeline;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class CohortManagerUnitTest {

    @Mock JedisProvider jedisProvider;
    @Mock Jedis jedis;
    @Mock Pipeline pipeline;

    private SchemaKeys schema;
    private CohortManager cohorts;

    @BeforeEach
    void setUp() {
        MockitoAnnotations.openMocks(this);
        when(jedisProvider.getResource()).thenReturn(jedis);
        when(jedis.pipelined()).thenReturn(pipeline);
        schema = new SchemaKeys("test");
        cohorts = new CohortManager(jedisProvider, schema);
    }

    // ── create ─────────────────────────────────────────────────

    @Test
    void createAddsToCohortIndex() {
        /*
         * Given: create("beta-testers") called.
         * Expected: SADD called on cohorts index key.
         */
        cohorts.create("beta-testers");
        verify(jedis).sadd(schema.cohortsIndex(), "beta-testers");
    }

    // ── delete ─────────────────────────────────────────────────

    @Test
    void deleteFetchesMembersBeforeDeleting() {
        /*
         * Given: delete("beta-testers") called.
         * Expected: SMEMBERS called first to get members for reverse index cleanup.
         */
        when(jedis.smembers(schema.cohort("beta-testers")))
            .thenReturn(Set.of("alice", "bob"));
        cohorts.delete("beta-testers");
        verify(jedis).smembers(schema.cohort("beta-testers"));
    }

    @Test
    void deleteCleansPipelineOperations() {
        /*
         * Given: delete("beta-testers") called. Two members: alice, bob.
         * Expected: pipeline executed — DEL and SREM called atomically.
         */
        when(jedis.smembers(schema.cohort("beta-testers")))
            .thenReturn(Set.of("alice", "bob"));
        cohorts.delete("beta-testers");
        verify(pipeline).del(schema.cohort("beta-testers"));
        verify(pipeline).srem(schema.cohortsIndex(), "beta-testers");
        verify(pipeline).sync();
    }

    @Test
    void deleteEmptyCohortNoPipelineSremForMembers() {
        /*
         * Given: delete() called on empty cohort — no members.
         * Expected: no SREM for user reverse index — nothing to clean.
         */
        when(jedis.smembers(schema.cohort("beta-testers")))
            .thenReturn(Set.of());
        cohorts.delete("beta-testers");
        verify(pipeline, never()).srem(contains("user"), any());
        verify(pipeline).sync();
    }

    // ── addUser ────────────────────────────────────────────────

    @Test
    void addUserWritesBothDirections() {
        /*
         * Given: addUser("beta-testers", "alice") called.
         * Expected: pipeline SADD on both directions atomically.
         *           Direction 1: cohort → members
         *           Direction 2: user → cohorts (reverse index)
         */
        cohorts.addUser("beta-testers", "alice");
        verify(pipeline).sadd(schema.cohort("beta-testers"), "alice");
        verify(pipeline).sadd(schema.userCohorts("alice"), "beta-testers");
        verify(pipeline).sync();
    }

    // ── removeUser ─────────────────────────────────────────────

    @Test
    void removeUserRemovesBothDirections() {
        /*
         * Given: removeUser("beta-testers", "alice") called.
         * Expected: pipeline SREM on both directions atomically.
         */
        cohorts.removeUser("beta-testers", "alice");
        verify(pipeline).srem(schema.cohort("beta-testers"), "alice");
        verify(pipeline).srem(schema.userCohorts("alice"), "beta-testers");
        verify(pipeline).sync();
    }

    // ── exists ─────────────────────────────────────────────────

    @Test
    void existsReturnsTrueWhenInIndex() {
        /*
         * Given: SISMEMBER returns true.
         * Expected: exists() returns true.
         */
        when(jedis.sismember(schema.cohortsIndex(), "beta-testers"))
            .thenReturn(true);
        assertTrue(cohorts.exists("beta-testers"));
    }

    @Test
    void existsReturnsFalseWhenNotInIndex() {
        /*
         * Given: SISMEMBER returns false.
         * Expected: exists() returns false.
         */
        when(jedis.sismember(schema.cohortsIndex(), "nonexistent"))
            .thenReturn(false);
        assertFalse(cohorts.exists("nonexistent"));
    }

    // ── listCohorts ────────────────────────────────────────────

    @Test
    void listCohortsCallsSMEMBERSOnIndex() {
        /*
         * Given: listCohorts() called.
         * Expected: SMEMBERS called on cohorts index — not KEYS *.
         */
        when(jedis.smembers(schema.cohortsIndex()))
            .thenReturn(Set.of("beta-testers", "premium-users"));
        var result = cohorts.listCohorts();
        verify(jedis).smembers(schema.cohortsIndex());
        assertTrue(result.contains("beta-testers"));
        assertTrue(result.contains("premium-users"));
    }

    @Test
    void listCohortsReturnsSorted() {
        /*
         * Given: three cohorts in random order.
         * Expected: listCohorts() returns alphabetically sorted list.
         */
        when(jedis.smembers(schema.cohortsIndex()))
            .thenReturn(Set.of("zebra", "alpha", "middle"));
        var result = cohorts.listCohorts();
        assertEquals("alpha",  result.get(0));
        assertEquals("middle", result.get(1));
        assertEquals("zebra",  result.get(2));
    }
}