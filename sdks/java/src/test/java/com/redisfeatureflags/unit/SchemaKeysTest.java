package com.redisfeatureflags.unit;

import com.redisfeatureflags.*;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class SchemaKeysTest {

    private final SchemaKeys keys = new SchemaKeys("prod");

    @Test
    void testFlagKey() {
        assertEquals("ff:prod:flag:dark_mode", keys.flag("dark_mode"));
    }

    @Test
    void testFlagUsersKey() {
        assertEquals("ff:prod:flag:dark_mode:users", keys.flagUsers("dark_mode"));
    }

    @Test
    void testFlagCohortsKey() {
        assertEquals("ff:prod:flag:dark_mode:cohorts", keys.flagCohorts("dark_mode"));
    }

    @Test
    void testFlagHistoryKey() {
        assertEquals("ff:prod:flag:dark_mode:history", keys.flagHistory("dark_mode"));
    }

    @Test
    void testCohortKey() {
        assertEquals("ff:prod:cohort:beta-testers", keys.cohort("beta-testers"));
    }

    @Test
    void testUserCohortsKey() {
        assertEquals("ff:prod:user:alice:cohorts", keys.userCohorts("alice"));
    }

    @Test
    void testFlagsIndexKey() {
        assertEquals("ff:prod:flags:__index__", keys.flagsIndex());
    }

    @Test
    void testCohortsIndexKey() {
        assertEquals("ff:prod:cohorts:__index__", keys.cohortsIndex());
    }

    @Test
    void testSchemaVersionKey() {
        assertEquals("ff:prod:__schema__", keys.schemaVersion());
    }

    @Test
    void testDifferentEnvironments() {
        SchemaKeys prod    = new SchemaKeys("prod");
        SchemaKeys staging = new SchemaKeys("staging");
        assertNotEquals(prod.flag("dark_mode"), staging.flag("dark_mode"));
        assertEquals("ff:prod:flag:dark_mode",    prod.flag("dark_mode"));
        assertEquals("ff:staging:flag:dark_mode", staging.flag("dark_mode"));
    }
}