# redis_feature_flags/cache.py

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CacheEntry:
    """
    A single cached flag object.
    Stores the raw flag data and when it was cached.
    """
    data: Dict[str, Any]
    cached_at: float = field(default_factory=time.monotonic)

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if this entry is older than the TTL."""
        age = time.monotonic() - self.cached_at
        return age > ttl_seconds


class LocalCache:
    """
    In-process cache for feature flag data.

    Serves flag data from memory to avoid a Redis call
    on every is_enabled() evaluation. Falls back to
    serving stale data if Redis becomes unreachable.

    Thread-safe — safe to use across multiple threads.
    """

    def __init__(self, ttl_seconds: int = 30):
        """
        Args:
            ttl_seconds: How long a cached flag is considered
                         fresh. Default 30 seconds.
                         After TTL expires, next read fetches
                         from Redis and refreshes the cache.
        """
        self._ttl = ttl_seconds
        self._store: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached flag if it exists and is not expired.

        Returns:
            Flag data dict if cached and fresh.
            None if not cached or expired.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.is_expired(self._ttl):
                return None
            return entry.data

    def get_stale(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached flag even if expired.
        Used as fallback when Redis is unreachable.

        Returns:
            Flag data dict if it exists in cache at all.
            None if never cached.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            return entry.data

    def set(self, key: str, data: Dict[str, Any]) -> None:
        """
        Store flag data in cache.

        Args:
            key: Cache key — typically the Redis flag key
            data: Flag data dict from Redis HGETALL
        """
        with self._lock:
            self._store[key] = CacheEntry(data=data)

    def delete(self, key: str) -> None:
        """
        Remove a flag from cache.
        Called when a flag is updated or deleted
        so the next read fetches fresh data from Redis.
        """
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """
        Remove all entries from cache.
        Useful for testing and for forcing a full refresh.
        """
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        """Number of entries currently in cache."""
        with self._lock:
            return len(self._store)

    def preload(self, flags: Dict[str, Dict[str, Any]]) -> None:
        """
        Load multiple flags into cache at once.
        Called on SDK startup to pre-warm the cache.

        Args:
            flags: Dict of {cache_key: flag_data}
        """
        with self._lock:
            for key, data in flags.items():
                self._store[key] = CacheEntry(data=data)