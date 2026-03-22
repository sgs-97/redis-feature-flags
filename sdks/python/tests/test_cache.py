import time
import threading
import pytest
from redis_feature_flags.cache import LocalCache, CacheEntry


# ── CacheEntry tests ──────────────────────────────────────────


def test_cache_entry_not_expired_immediately():
    """
    Given: a brand new cache entry just created.
    Expected: is_expired() returns False.
    """
    entry = CacheEntry(data={"enabled": "1"})
    assert entry.is_expired(ttl_seconds=30) is False


def test_cache_entry_expired_after_ttl():
    """
    Given: a cache entry backdated 31 seconds ago. TTL is 30.
    Expected: is_expired() returns True.
    """
    entry = CacheEntry(data={"enabled": "1"})
    entry.cached_at = time.monotonic() - 31
    assert entry.is_expired(ttl_seconds=30) is True


def test_cache_entry_not_expired_before_ttl():
    """
    Given: a cache entry backdated 29 seconds ago. TTL is 30.
    Expected: is_expired() returns False — still within TTL window.
    """
    entry = CacheEntry(data={"enabled": "1"})
    entry.cached_at = time.monotonic() - 29
    assert entry.is_expired(ttl_seconds=30) is False


# ── LocalCache tests ──────────────────────────────────────────


def test_get_returns_none_when_empty():
    """
    Given: empty cache.
    Expected: get() returns None — key does not exist.
    """
    cache = LocalCache()
    assert cache.get("ff:prod:flag:dark_mode") is None


def test_set_and_get():
    """
    Given: a flag stored in cache.
    Expected: get() returns the exact same data that was stored.
    """
    cache = LocalCache()
    data = {"enabled": "1", "rollout": "10"}
    cache.set("ff:prod:flag:dark_mode", data)
    assert cache.get("ff:prod:flag:dark_mode") == data


def test_get_returns_none_after_expiry():
    """
    Given: a flag stored then backdated 31 seconds. TTL is 30.
    Expected: get() returns None — entry is expired.
    """
    cache = LocalCache(ttl_seconds=30)
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    cache._store["ff:prod:flag:dark_mode"].cached_at = time.monotonic() - 31
    assert cache.get("ff:prod:flag:dark_mode") is None


def test_expired_entry_stays_for_stale_access():
    """
    Given: an expired cache entry.
    Expected: get() returns None but entry still exists in _store
              so get_stale() can serve it when Redis is down.
    """
    cache = LocalCache(ttl_seconds=30)
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    cache._store["ff:prod:flag:dark_mode"].cached_at = time.monotonic() - 31
    assert cache.get("ff:prod:flag:dark_mode") is None
    assert "ff:prod:flag:dark_mode" in cache._store


def test_get_stale_returns_expired_data():
    """
    Given: an expired cache entry.
    Expected: get() returns None (too old) but get_stale() still
              returns the data — used as fallback when Redis is unreachable.
    """
    cache = LocalCache(ttl_seconds=30)
    data = {"enabled": "1"}
    cache.set("ff:prod:flag:dark_mode", data)
    cache._store["ff:prod:flag:dark_mode"].cached_at = time.monotonic() - 31
    assert cache.get("ff:prod:flag:dark_mode") is None
    assert cache.get_stale("ff:prod:flag:dark_mode") == data


def test_get_stale_returns_none_when_never_cached():
    """
    Given: empty cache — flag was never stored.
    Expected: get_stale() returns None — nothing to serve.
    """
    cache = LocalCache()
    assert cache.get_stale("ff:prod:flag:nonexistent") is None


def test_delete_removes_entry():
    """
    Given: a flag stored in cache.
    After: delete() is called.
    Expected: get() returns None — entry is gone.
    """
    cache = LocalCache()
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    cache.delete("ff:prod:flag:dark_mode")
    assert cache.get("ff:prod:flag:dark_mode") is None


def test_delete_nonexistent_key_no_error():
    """
    Given: empty cache.
    After: delete() called on a key that does not exist.
    Expected: no exception raised — safe to call on missing keys.
    """
    cache = LocalCache()
    cache.delete("ff:prod:flag:nonexistent")


def test_clear_removes_all_entries():
    """
    Given: two flags stored in cache.
    After: clear() is called.
    Expected: cache size is 0 — all entries removed.
    """
    cache = LocalCache()
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    cache.set("ff:prod:flag:new_checkout", {"enabled": "0"})
    cache.clear()
    assert cache.size() == 0


def test_size_reflects_entries():
    """
    Given: flags being added and deleted one by one.
    Expected: size() reflects the exact count at each step.
    """
    cache = LocalCache()
    assert cache.size() == 0
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    assert cache.size() == 1
    cache.set("ff:prod:flag:new_checkout", {"enabled": "0"})
    assert cache.size() == 2
    cache.delete("ff:prod:flag:dark_mode")
    assert cache.size() == 1


def test_preload_sets_multiple_flags():
    """
    Given: a dictionary of two flags passed to preload().
    Expected: both flags retrievable and cache size is 2.
              Used on SDK startup to pre-warm cache from Redis.
    """
    cache = LocalCache()
    flags = {
        "ff:prod:flag:dark_mode":    {"enabled": "1", "rollout": "10"},
        "ff:prod:flag:new_checkout": {"enabled": "0", "rollout": "0"},
    }
    cache.preload(flags)
    assert cache.size() == 2
    assert cache.get("ff:prod:flag:dark_mode") == flags["ff:prod:flag:dark_mode"]
    assert cache.get("ff:prod:flag:new_checkout") == flags["ff:prod:flag:new_checkout"]


def test_custom_ttl():
    """
    Given: cache with 60 second TTL. Entry backdated 45 seconds.
    Expected: get() still returns data — 45 seconds is within 60 second TTL.
    """
    cache = LocalCache(ttl_seconds=60)
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    cache._store["ff:prod:flag:dark_mode"].cached_at = time.monotonic() - 45
    assert cache.get("ff:prod:flag:dark_mode") is not None


# ── Thread safety tests ───────────────────────────────────────


def test_thread_safe_concurrent_writes():
    """
    Given: 10 threads each writing 100 different flags simultaneously.
    Expected: no exceptions raised — lock prevents data corruption.
    """
    cache = LocalCache()
    errors = []

    def write_flags(thread_id: int):
        try:
            for i in range(100):
                key = f"ff:prod:flag:flag_{thread_id}_{i}"
                cache.set(key, {"enabled": "1", "thread": str(thread_id)})
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=write_flags, args=(i,))
        for i in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0


def test_thread_safe_concurrent_reads_and_writes():
    """
    Given: 5 threads reading and 5 threads writing the same key simultaneously.
    Expected: no exceptions raised — reads and writes do not corrupt each other.
    """
    cache = LocalCache()
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    errors = []

    def reader():
        try:
            for _ in range(100):
                cache.get("ff:prod:flag:dark_mode")
        except Exception as e:
            errors.append(e)

    def writer():
        try:
            for i in range(100):
                cache.set(
                    "ff:prod:flag:dark_mode",
                    {"enabled": "1", "rollout": str(i)}
                )
        except Exception as e:
            errors.append(e)

    threads = (
        [threading.Thread(target=reader) for _ in range(5)] +
        [threading.Thread(target=writer) for _ in range(5)]
    )
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0