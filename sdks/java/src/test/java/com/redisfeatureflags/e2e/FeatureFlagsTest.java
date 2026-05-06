package com.redisfeatureflags.e2e;

import com.redisfeatureflags.*;

import com.redisfeatureflags.exceptions.FlagNotFoundError;
import com.redisfeatureflags.exceptions.InvalidRolloutError;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;

import static org.junit.jupiter.api.Assertions.*;

class FeatureFlagsTest {

    private JedisPool jedisPool;
    private FeatureFlags flags;

    @BeforeEach
    void setUp() {
        jedisPool = new JedisPool("localhost", 6379);
        flags = new FeatureFlags(jedisPool, "test");
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
    void createFlagDisabledByDefault() {
        /*
         * Given: flag created with no arguments.
         * Expected: isEnabled() returns false — disabled by default.
         */
        flags.create("dark_mode");
        assertFalse(flags.isEnabled("dark_mode", "alice"));
    }

    @Test
    void createFlagInvalidRolloutRaises() {
        /*
         * Given: create() called with rollout=150.
         * Expected: InvalidRolloutError — rollout must be 0-100.
         */
        assertThrows(InvalidRolloutError.class,
            () -> flags.create("dark_mode", 150));
    }

    @Test
    void createFlagNegativeRolloutRaises() {
        /*
         * Given: create() called with rollout=-1.
         * Expected: InvalidRolloutError raised.
         */
        assertThrows(InvalidRolloutError.class,
            () -> flags.create("dark_mode", -1));
    }

    @Test
    void createMultipleFlagsAllInList() {
        /*
         * Given: three flags created.
         * Expected: listFlags() returns all three names.
         */
        flags.create("dark_mode");
        flags.create("new_checkout");
        flags.create("ai_search");
        assertTrue(flags.listFlags().contains("dark_mode"));
        assertTrue(flags.listFlags().contains("new_checkout"));
        assertTrue(flags.listFlags().contains("ai_search"));
    }

    // ── enable ─────────────────────────────────────────────────

    @Test
    void enableFlagIsEnabledReturnsTrue() {
        /*
         * Given: flag created, enabled, rollout=100.
         * Expected: isEnabled() returns true for any user.
         */
        flags.create("dark_mode", 100);
        flags.enable("dark_mode");
        assertTrue(flags.isEnabled("dark_mode", "alice"));
    }

    @Test
    void enableNonexistentFlagRaises() {
        /*
         * Given: flag does not exist.
         * Expected: FlagNotFoundError raised.
         */
        assertThrows(FlagNotFoundError.class,
            () -> flags.enable("nonexistent"));
    }

    // ── disable ────────────────────────────────────────────────

    @Test
    void disableFlagIsEnabledReturnsFalse() {
        /*
         * Given: flag enabled with rollout=100 then disabled.
         * Expected: isEnabled() returns false — kill switch works.
         */
        flags.create("dark_mode", 100);
        flags.enable("dark_mode");
        flags.disable("dark_mode");
        assertFalse(flags.isEnabled("dark_mode", "alice"));
    }

    @Test
    void disableNonexistentFlagRaises() {
        /*
         * Given: flag does not exist.
         * Expected: FlagNotFoundError raised.
         */
        assertThrows(FlagNotFoundError.class,
            () -> flags.disable("nonexistent"));
    }

    // ── setRollout ─────────────────────────────────────────────

    @Test
    void setRolloutHundredAllUsersGetFlag() {
        /*
         * Given: flag enabled, rollout set to 100.
         * Expected: isEnabled() returns true for all users.
         */
        flags.create("dark_mode");
        flags.enable("dark_mode");
        flags.setRollout("dark_mode", 100);
        assertTrue(flags.isEnabled("dark_mode", "alice"));
        assertTrue(flags.isEnabled("dark_mode", "bob"));
        assertTrue(flags.isEnabled("dark_mode", "charlie"));
    }

    @Test
    void setRolloutZeroNoUsersGetFlag() {
        /*
         * Given: flag enabled, rollout set to 0.
         * Expected: isEnabled() returns false for all users
         *           unless in allowlist or cohort.
         */
        flags.create("dark_mode");
        flags.enable("dark_mode");
        flags.setRollout("dark_mode", 0);
        assertFalse(flags.isEnabled("dark_mode", "alice"));
    }

    @Test
    void setRolloutInvalidRaises() {
        /*
         * Given: setRollout() called with 150.
         * Expected: InvalidRolloutError raised.
         */
        flags.create("dark_mode");
        assertThrows(InvalidRolloutError.class,
            () -> flags.setRollout("dark_mode", 150));
    }

    @Test
    void setRolloutNonexistentFlagRaises() {
        /*
         * Given: flag does not exist.
         * Expected: FlagNotFoundError raised.
         */
        assertThrows(FlagNotFoundError.class,
            () -> flags.setRollout("nonexistent", 50));
    }

    // ── delete ─────────────────────────────────────────────────

    @Test
    void deleteFlagIsEnabledReturnsDefault() {
        /*
         * Given: flag created, enabled, then deleted.
         * Expected: isEnabled() returns false — flag gone.
         */
        flags.create("dark_mode", 100);
        flags.enable("dark_mode");
        flags.delete("dark_mode");
        assertFalse(flags.isEnabled("dark_mode", "alice"));
    }

    @Test
    void deleteFlagRemovedFromList() {
        /*
        * Given: two flags. dark_mode deleted.
        * Expected: listFlags() no longer contains dark_mode.
        */
        flags.create("dark_mode");
        flags.create("new_checkout");
        flags.delete("dark_mode");
        assertFalse(flags.listFlags().contains("dark_mode"));
        assertTrue(flags.listFlags().contains("new_checkout"));
    }

    @Test
void listFlagsEmptyWhenNoneCreated() {
    /*
     * Given: no flags created.
     * Expected: listFlags() returns empty list.
     */
    assertTrue(flags.listFlags().isEmpty());
}

@Test
void listFlagsSorted() {
    /*
     * Given: flags created in random order.
     * Expected: listFlags() returns sorted list.
     */
    flags.create("zebra_flag");
    flags.create("alpha_flag");
    flags.create("middle_flag");
    var list = flags.listFlags();
    assertEquals("alpha_flag",  list.get(0));
    assertEquals("middle_flag", list.get(1));
    assertEquals("zebra_flag",  list.get(2));
}

@Test
void missingFlagReturnsDefaultFalse() {
    /*
     * Given: flag does not exist.
     * Expected: isEnabled() returns false — default.
     */
    assertFalse(flags.isEnabled("nonexistent", "alice"));
}

@Test
void missingFlagReturnsCustomDefault() {
    /*
     * Given: flag does not exist.
     * Expected: isEnabled() returns true — custom default.
     */
    assertTrue(flags.isEnabled("nonexistent", "alice", true));
}
}