package com.redisfeatureflags;

import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class LocalCache {

    private static class CacheEntry {
        final Map<String, String> data;
        final long cachedAt;

        CacheEntry(Map<String, String> data) {
            this.data = data;
            this.cachedAt = System.currentTimeMillis(); // milliseconds
        }

        boolean isExpired(int ttlSeconds) {
            long ageMs = System.currentTimeMillis() - cachedAt;
            return ageMs > (ttlSeconds * 1000L);
        }
    }

    private final int ttlSeconds;
    private final ConcurrentHashMap<String, CacheEntry> store;

    public LocalCache(int ttlSeconds) {
        this.ttlSeconds = ttlSeconds;
        this.store = new ConcurrentHashMap<>();
    }

    public LocalCache() {
        this(30);
    }

    /**
     * Get fresh data — null if missing or expired.
     */
    public Map<String, String> get(String key) {
        CacheEntry entry = store.get(key);
        if (entry == null) return null;
        if (entry.isExpired(ttlSeconds)) return null;
        return entry.data;
    }

    /**
     * Get stale data — returns even if expired.
     * Used as fallback when Redis is down.
     */
    public Map<String, String> getStale(String key) {
        CacheEntry entry = store.get(key);
        if (entry == null) return null;
        return entry.data;
    }

    /**
     * Store data in cache.
     */
    public void set(String key, Map<String, String> data) {
        store.put(key, new CacheEntry(data));
    }

    /**
     * Remove entry — called on flag update.
     */
    public void delete(String key) {
        store.remove(key);
    }

    /**
     * Remove all entries.
     */
    public void clear() {
        store.clear();
    }

    public int size() {
        return store.size();
    }
}