package com.redisfeatureflags.e2e;

import com.redisfeatureflags.*;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import static org.junit.jupiter.api.Assertions.*;

class CohortManagerTest {

    private JedisPool jedisPool;
    private SchemaKeys schema;
    private CohortManager cohorts;

    @BeforeEach
    void setUp() {
        jedisPool = new JedisPool("localhost", 6379);
        schema = new SchemaKeys("test");
        cohorts = new CohortManager(jedisPool::getResource, schema);
    }

    @AfterEach
    void tearDown() {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.flushAll();
        }
        jedisPool.close();
    }

    // ── create ─────────────────────────────────────────────────

    @Test
    void createCohortExistsInIndex() {
        /*
         * Given: create("beta-testers") called.
         * Expected: exists() returns true — registered in index.
         */
        cohorts.create("beta-testers");
        assertTrue(cohorts.exists("beta-testers"));
    }

    @Test
    void existsReturnsFalseForNonexistent() {
        /*
         * Given: cohort never created.
         * Expected: exists() returns false.
         */
        assertFalse(cohorts.exists("nonexistent"));
    }

    // ── delete ─────────────────────────────────────────────────

    @Test
    void deleteCohortRemovedFromIndex() {
        /*
         * Given: cohort created then deleted.
         * Expected: exists() returns false.
         */
        cohorts.create("beta-testers");
        cohorts.delete("beta-testers");
        assertFalse(cohorts.exists("beta-testers"));
    }

    @Test
    void deleteCohortRemovesMembersSet() {
        /*
         * Given: cohort with alice and bob, then deleted.
         * Expected: getMembers() returns empty set.
         */
        cohorts.addUser("beta-testers", "alice");
        cohorts.addUser("beta-testers", "bob");
        cohorts.delete("beta-testers");
        assertTrue(cohorts.getMembers("beta-testers").isEmpty());
    }

    @Test
    void deleteCohortCleansUserReverseIndex() {
        /*
         * Given: alice in beta-testers. Cohort deleted.
         * Expected: alice's reverse index no longer contains beta-testers.
         *           Both directions of bidirectional index cleaned.
         */
        cohorts.addUser("beta-testers", "alice");
        cohorts.delete("beta-testers");
        try (Jedis jedis = jedisPool.getResource()) {
            assertFalse(jedis.sismember(schema.userCohorts("alice"), "beta-testers"));
        }
    }

    @Test
    void deleteCohortPreservesOtherCohorts() {
        /*
         * Given: alice in beta-testers and premium-users.
         *        beta-testers deleted.
         * Expected: alice still in premium-users reverse index.
         */
        cohorts.addUser("beta-testers", "alice");
        cohorts.addUser("premium-users", "alice");
        cohorts.delete("beta-testers");
        try (Jedis jedis = jedisPool.getResource()) {
            assertTrue(jedis.sismember(schema.userCohorts("alice"), "premium-users"));
            assertFalse(jedis.sismember(schema.userCohorts("alice"), "beta-testers"));
        }
    }

    // ── addUser ────────────────────────────────────────────────

    @Test
    void addUserAppearsInMembers() {
        /*
         * Given: alice added to beta-testers.
         * Expected: alice in getMembers() result.
         */
        cohorts.addUser("beta-testers", "alice");
        assertTrue(cohorts.getMembers("beta-testers").contains("alice"));
    }

    @Test
    void addUserUpdatesReverseIndex() {
        /*
         * Given: alice added to beta-testers.
         * Expected: beta-testers in alice's reverse index.
         *           Direction 2 of bidirectional index must stay in sync.
         */
        cohorts.addUser("beta-testers", "alice");
        try (Jedis jedis = jedisPool.getResource()) {
            assertTrue(jedis.sismember(schema.userCohorts("alice"), "beta-testers"));
        }
    }

    @Test
    void userInMultipleCohorts() {
        /*
         * Given: alice added to beta-testers and premium-users.
         * Expected: both cohorts in alice's reverse index.
         *           User can belong to multiple cohorts simultaneously.
         */
        cohorts.addUser("beta-testers", "alice");
        cohorts.addUser("premium-users", "alice");
        try (Jedis jedis = jedisPool.getResource()) {
            assertTrue(jedis.sismember(schema.userCohorts("alice"), "beta-testers"));
            assertTrue(jedis.sismember(schema.userCohorts("alice"), "premium-users"));
        }
    }

    // ── removeUser ─────────────────────────────────────────────

    @Test
    void removeUserNotInMembers() {
        /*
         * Given: alice added then removed from beta-testers.
         * Expected: alice not in getMembers() result.
         */
        cohorts.addUser("beta-testers", "alice");
        cohorts.removeUser("beta-testers", "alice");
        assertFalse(cohorts.getMembers("beta-testers").contains("alice"));
    }

    @Test
    void removeUserUpdatesReverseIndex() {
        /*
         * Given: alice added then removed from beta-testers.
         * Expected: beta-testers not in alice's reverse index.
         *           Both directions cleaned on remove.
         */
        cohorts.addUser("beta-testers", "alice");
        cohorts.removeUser("beta-testers", "alice");
        try (Jedis jedis = jedisPool.getResource()) {
            assertFalse(jedis.sismember(schema.userCohorts("alice"), "beta-testers"));
        }
    }

    // ── getMembers ─────────────────────────────────────────────

    @Test
    void getMembersEmptyForNonexistent() {
        /*
         * Given: cohort never created or has no members.
         * Expected: getMembers() returns empty set — no error.
         */
        assertTrue(cohorts.getMembers("nonexistent").isEmpty());
    }

    // ── listCohorts ────────────────────────────────────────────

    @Test
    void listCohortsReturnsAllCreated() {
        /*
         * Given: two cohorts created.
         * Expected: listCohorts() returns both names.
         */
        cohorts.create("beta-testers");
        cohorts.create("premium-users");
        assertTrue(cohorts.listCohorts().contains("beta-testers"));
        assertTrue(cohorts.listCohorts().contains("premium-users"));
    }

    @Test
    void listCohortsEmptyWhenNoneCreated() {
        /*
         * Given: no cohorts created.
         * Expected: listCohorts() returns empty list.
         */
        assertTrue(cohorts.listCohorts().isEmpty());
    }

    @Test
    void listCohortsExcludesDeleted() {
        /*
         * Given: beta-testers and premium-users created. beta-testers deleted.
         * Expected: listCohorts() returns only premium-users.
         */
        cohorts.create("beta-testers");
        cohorts.create("premium-users");
        cohorts.delete("beta-testers");
        assertFalse(cohorts.listCohorts().contains("beta-testers"));
        assertTrue(cohorts.listCohorts().contains("premium-users"));
    }
}