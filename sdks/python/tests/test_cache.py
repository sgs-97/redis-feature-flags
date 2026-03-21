# tests/test_cache.py

import time
import threading
import pytest
from redis_feature_flags.cache import LocalCache, CacheEntry


# ── CacheEntry tests ──────────────────────────────────────────


def test_cache_entry_not_expired_immediately():
    entry = CacheEntry(data={"enabled": "1"})
    assert entry.is_expired(ttl_seconds=30) is False


def test_cache_entry_expired_after_ttl():
    entry = CacheEntry(data={"enabled": "1"})
    # manually backdate the cached_at time
    entry.cached_at = time.monotonic() - 31
    assert entry.is_expired(ttl_seconds=30) is True


def test_cache_entry_not_expired_before_ttl():
    entry = CacheEntry(data={"enabled": "1"})
    entry.cached_at = time.monotonic() - 29
    assert entry.is_expired(ttl_seconds=30) is False


# ── LocalCache tests ──────────────────────────────────────────


def test_get_returns_none_when_empty():
    cache = LocalCache()
    assert cache.get("ff:prod:flag:dark_mode") is None


def test_set_and_get():
    cache = LocalCache()
    data = {"enabled": "1", "rollout": "10"}
    cache.set("ff:prod:flag:dark_mode", data)
    result = cache.get("ff:prod:flag:dark_mode")
    assert result == data


def test_get_returns_none_after_expiry():
    cache = LocalCache(ttl_seconds=30)
    data = {"enabled": "1"}
    cache.set("ff:prod:flag:dark_mode", data)

    # backdate the entry
    cache._store["ff:prod:flag:dark_mode"].cached_at = (
        time.monotonic() - 31
    )

    assert cache.get("ff:prod:flag:dark_mode") is None


def test_expired_entry_stays_for_stale_access():
    cache = LocalCache(ttl_seconds=30)
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    cache._store["ff:prod:flag:dark_mode"].cached_at = (
        time.monotonic() - 31
    )

    assert cache.get("ff:prod:flag:dark_mode") is None
    assert "ff:prod:flag:dark_mode" in cache._store


def test_get_stale_returns_expired_data():
    cache = LocalCache(ttl_seconds=30)
    data = {"enabled": "1"}
    cache.set("ff:prod:flag:dark_mode", data)
    cache._store["ff:prod:flag:dark_mode"].cached_at = (
        time.monotonic() - 31
    )

    # get() returns None — expired
    assert cache.get("ff:prod:flag:dark_mode") is None

    # get_stale() returns data even though expired
    assert cache.get_stale("ff:prod:flag:dark_mode") == data


def test_get_stale_returns_none_when_never_cached():
    cache = LocalCache()
    assert cache.get_stale("ff:prod:flag:nonexistent") is None


def test_delete_removes_entry():
    cache = LocalCache()
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    cache.delete("ff:prod:flag:dark_mode")
    assert cache.get("ff:prod:flag:dark_mode") is None


def test_delete_nonexistent_key_no_error():
    cache = LocalCache()
    cache.delete("ff:prod:flag:nonexistent")  # should not raise


def test_clear_removes_all_entries():
    cache = LocalCache()
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    cache.set("ff:prod:flag:new_checkout", {"enabled": "0"})
    cache.clear()
    assert cache.size() == 0


def test_size_reflects_entries():
    cache = LocalCache()
    assert cache.size() == 0
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    assert cache.size() == 1
    cache.set("ff:prod:flag:new_checkout", {"enabled": "0"})
    assert cache.size() == 2
    cache.delete("ff:prod:flag:dark_mode")
    assert cache.size() == 1


def test_preload_sets_multiple_flags():
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
    cache = LocalCache(ttl_seconds=60)
    cache.set("ff:prod:flag:dark_mode", {"enabled": "1"})
    cache._store["ff:prod:flag:dark_mode"].cached_at = (
        time.monotonic() - 45
    )
    # 45 seconds < 60 second TTL — should still be fresh
    assert cache.get("ff:prod:flag:dark_mode") is not None


# ── Thread safety tests ───────────────────────────────────────


def test_thread_safe_concurrent_writes():
    """Multiple threads writing simultaneously should not corrupt data."""
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
    """Reading and writing simultaneously should not cause errors."""
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