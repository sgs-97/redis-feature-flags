package featureflags

import (
	"sync"
	"time"
)

// cacheEntry holds flag data and the time it was cached.
type cacheEntry struct {
	data     map[string]string
	cachedAt time.Time
}

// isExpired returns true if the entry is older than ttl.
func (e *cacheEntry) isExpired(ttl time.Duration) bool {
	return time.Since(e.cachedAt) > ttl
}

// LocalCache is an in-process cache for flag data.
// Thread-safe via sync.RWMutex.
// Serves stale data when Redis is down — application never crashes.
type LocalCache struct {
	mu    sync.RWMutex
	store map[string]*cacheEntry
	ttl   time.Duration
}

// NewLocalCache creates a new LocalCache with the given TTL in seconds.
func NewLocalCache(ttlSeconds int) *LocalCache {
	return &LocalCache{
		store: make(map[string]*cacheEntry),
		ttl:   time.Duration(ttlSeconds) * time.Second,
	}
}

// Get returns fresh cache data — nil if missing or expired.
func (c *LocalCache) Get(key string) map[string]string {
	c.mu.RLock()
	defer c.mu.RUnlock()

	entry, ok := c.store[key]
	if !ok {
		return nil
	}
	if entry.isExpired(c.ttl) {
		return nil
	}
	return entry.data
}

// GetStale returns cache data even if expired.
// Used as fallback when Redis is down.
func (c *LocalCache) GetStale(key string) map[string]string {
	c.mu.RLock()
	defer c.mu.RUnlock()

	entry, ok := c.store[key]
	if !ok {
		return nil
	}
	return entry.data
}

// Set stores data in cache.
func (c *LocalCache) Set(key string, data map[string]string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.store[key] = &cacheEntry{
		data:     data,
		cachedAt: time.Now(),
	}
}

// Delete removes an entry from cache.
// Called on enable(), disable(), setRollout(), delete().
func (c *LocalCache) Delete(key string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	delete(c.store, key)
}

// Clear removes all entries from cache.
func (c *LocalCache) Clear() {
	c.mu.Lock()
	defer c.mu.Unlock()

	c.store = make(map[string]*cacheEntry)
}

// Size returns the number of entries in cache.
func (c *LocalCache) Size() int {
	c.mu.RLock()
	defer c.mu.RUnlock()

	return len(c.store)
}