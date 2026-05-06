package com.redisfeatureflags.unit;

import com.redisfeatureflags.*;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class UtilsTest {

    // ── evaluateRollout ────────────────────────────────────────

    @Test
    void rolloutZeroAlwaysFalse() {
        /*
         * Given: rollout=0
         * Expected: false — nobody in a 0% rollout
         */
        assertFalse(Utils.evaluateRollout("dark_mode", "alice", 0));
    }

    @Test
    void rolloutHundredAlwaysTrue() {
        /*
         * Given: rollout=100
         * Expected: true — everyone in a 100% rollout
         */
        assertTrue(Utils.evaluateRollout("dark_mode", "alice", 100));
    }

    @Test
    void rolloutDeterministic() {
        /*
         * Given: same flag, same user, same rollout — called twice
         * Expected: both calls return same result
         *           SHA-256 hashing is deterministic — no randomness
         */
        boolean result1 = Utils.evaluateRollout("dark_mode", "alice", 50);
        boolean result2 = Utils.evaluateRollout("dark_mode", "alice", 50);
        assertEquals(result1, result2);
    }

    @Test
    void rolloutConsistentAcrossManyCalls() {
        /*
         * Given: same user evaluated 1000 times at rollout=30
         * Expected: all 1000 results identical
         *           confirms zero randomness
         */
        boolean first = Utils.evaluateRollout("dark_mode", "bob", 30);
        for (int i = 0; i < 1000; i++) {
            assertEquals(first, Utils.evaluateRollout("dark_mode", "bob", 30));
        }
    }

    @Test
    void rolloutDistributesUsersEvenly() {
        /*
         * Given: 1000 different users at rollout=50
         * Expected: roughly half get true — between 300 and 700
         *           confirms even distribution across user population
         */
        int trueCount = 0;
        for (int i = 0; i < 1000; i++) {
            if (Utils.evaluateRollout("dark_mode", "user_" + i, 50)) {
                trueCount++;
            }
        }
        assertTrue(trueCount >= 300 && trueCount <= 700,
            "Expected ~500 true but got " + trueCount);
    }

    @Test
    void rolloutFlagNameAffectsResult() {
        /*
         * Given: same user, different flag names, rollout=50
         * Expected: at least one different result
         *           flag name included in hash — flags have independent buckets
         */
        String[] flags = {"flag_a", "flag_b", "flag_c", "flag_d", "flag_e"};
        boolean first = Utils.evaluateRollout(flags[0], "alice", 50);
        boolean allSame = true;
        for (String flag : flags) {
            if (Utils.evaluateRollout(flag, "alice", 50) != first) {
                allSame = false;
                break;
            }
        }
        assertFalse(allSame, "Expected different results across flag names");
    }

    // ── isExpired ──────────────────────────────────────────────

    @Test
    void zeroNeverExpires() {
        /*
         * Given: expires_at=0
         * Expected: false — 0 means never expires
         */
        assertFalse(Utils.isExpired(0));
    }

    @Test
    void pastTimestampExpired() {
        /*
         * Given: expires_at=1000 (unix 1000 = year 1970 — definitely past)
         * Expected: true — flag has expired
         */
        assertTrue(Utils.isExpired(1000));
    }

    @Test
    void futureTimestampNotExpired() {
        /*
         * Given: expires_at = now + 86400 (24 hours in future)
         * Expected: false — flag has not expired yet
         */
        long future = Utils.nowUnix() + 86400;
        assertFalse(Utils.isExpired(future));
    }

    // ── nowUnix ────────────────────────────────────────────────

    @Test
    void nowUnixIsRecent() {
        /*
         * Given: call to nowUnix()
         * Expected: within 1 second of System.currentTimeMillis()
         *           confirms UTC unix timestamp accuracy
         */
        long now = Utils.nowUnix();
        long systemNow = System.currentTimeMillis() / 1000;
        assertTrue(Math.abs(now - systemNow) <= 1);
    }

    @Test
    void nowUnixIsPositive() {
        /*
         * Given: call to nowUnix()
         * Expected: positive value — sanity check
         */
        assertTrue(Utils.nowUnix() > 0);
    }
}