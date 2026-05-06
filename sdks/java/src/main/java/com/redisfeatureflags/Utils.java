package com.redisfeatureflags;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;

public class Utils {

    /**
     * Deterministic rollout hashing.
     * Same flag + user always returns same bucket.
     * SHA-256 of "flagName:userId" modulo 100.
     */
    public static boolean evaluateRollout(String flagName, String userId, int rollout) {
        if (rollout <= 0) return false;
        if (rollout >= 100) return true;

        try {
            String key = flagName + ":" + userId;
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(key.getBytes(StandardCharsets.UTF_8));

            // take first 4 bytes as unsigned int
            long value = ((hash[0] & 0xFFL) << 24)
                       | ((hash[1] & 0xFFL) << 16)
                       | ((hash[2] & 0xFFL) << 8)
                       |  (hash[3] & 0xFFL);

            int bucket = (int)(value % 100);
            return bucket < rollout;

        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException("SHA-256 not available", e);
        }
    }

    /**
     * Current unix timestamp in seconds — UTC.
     */
    public static long nowUnix() {
        return Instant.now().getEpochSecond();
    }

    /**
     * Check if a unix timestamp has passed.
     * 0 means never expires.
     */
    public static boolean isExpired(long expiresAt) {
        if (expiresAt == 0) return false;
        return nowUnix() > expiresAt;
    }
}