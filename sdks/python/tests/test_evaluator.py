from __future__ import annotations

import pytest
import fakeredis
import redis

from redis_feature_flags.cache import LocalCache
from redis_feature_flags.evaluator import Evaluator
from redis_feature_flags.schema import SchemaKeys


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis()

@pytest.fixture
def schema():
    return SchemaKeys(env="test")

@pytest.fixture
def cache():
    return LocalCache(ttl_seconds=30)

@pytest.fixture
def evaluator(redis_client, schema, cache):
    return Evaluator(redis_client, schema, cache)


def create_flag(redis_client, schema, flag_name, **kwargs):
    """Helper — creates a flag in fake Redis with sensible defaults."""
    defaults = {"enabled": "1", "rollout": "0", "expires_at": "0", "flag_version": "1"}
    defaults.update(kwargs)
    redis_client.hset(schema.flag(flag_name), mapping=defaults)


# ── Flag missing ───────────────────────────────────────────────


def test_missing_flag_returns_default_false(evaluator):
    """
    Given: flag does not exist in Redis or cache.
    Expected: is_enabled() returns False — the default.
    """
    assert evaluator.is_enabled("nonexistent", "alice") is False


def test_missing_flag_returns_custom_default(evaluator):
    """
    Given: flag does not exist in Redis or cache.
    Expected: is_enabled() returns True — the custom default passed by caller.
    """
    assert evaluator.is_enabled("nonexistent", "alice", default=True) is True


# ── Kill switch ────────────────────────────────────────────────


def test_disabled_flag_returns_false(evaluator, redis_client, schema):
    """
    Given: flag exists with enabled=0 and rollout=100.
    Expected: is_enabled() returns False — kill switch overrides everything.
    """
    create_flag(redis_client, schema, "dark_mode", enabled="0", rollout="100")
    assert evaluator.is_enabled("dark_mode", "alice") is False


def test_enabled_flag_with_zero_rollout_returns_false(evaluator, redis_client, schema):
    """
    Given: flag exists with enabled=1 but rollout=0.
    Expected: is_enabled() returns False — nobody is in a 0% rollout.
    """
    create_flag(redis_client, schema, "dark_mode", enabled="1", rollout="0")
    assert evaluator.is_enabled("dark_mode", "alice") is False


# ── Expiry ─────────────────────────────────────────────────────


def test_expired_flag_returns_false(evaluator, redis_client, schema):
    """
    Given: flag with expires_at=1000 (unix 1000 = year 1970 — definitely past).
    Expected: is_enabled() returns False — flag has expired.
    """
    create_flag(redis_client, schema, "dark_mode", enabled="1", rollout="100", expires_at="1000")
    assert evaluator.is_enabled("dark_mode", "alice") is False


def test_future_expiry_does_not_block(evaluator, redis_client, schema):
    """
    Given: flag with expires_at set 24 hours in the future.
    Expected: is_enabled() returns True — flag has not expired yet.
    """
    from redis_feature_flags.utils import now_unix
    future = str(now_unix() + 86400)
    create_flag(redis_client, schema, "dark_mode", enabled="1", rollout="100", expires_at=future)
    assert evaluator.is_enabled("dark_mode", "alice") is True


def test_no_expiry_zero_does_not_block(evaluator, redis_client, schema):
    """
    Given: flag with expires_at=0 meaning never expires.
    Expected: is_enabled() returns True — flag runs forever.
    """
    create_flag(redis_client, schema, "dark_mode", enabled="1", rollout="100", expires_at="0")
    assert evaluator.is_enabled("dark_mode", "alice") is True


# ── User allowlist ─────────────────────────────────────────────


def test_user_in_allowlist_returns_true(evaluator, redis_client, schema):
    """
    Given: flag with rollout=0. Alice is in the user allowlist.
    Expected: is_enabled() returns True — allowlist overrides rollout.
    """
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_users("dark_mode"), "alice")
    assert evaluator.is_enabled("dark_mode", "alice") is True


def test_user_not_in_allowlist_continues_to_rollout(evaluator, redis_client, schema):
    """
    Given: flag with rollout=0. Bob is in the allowlist but Alice is not.
    Expected: is_enabled() for Alice returns False — not in allowlist, rollout is 0.
    """
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_users("dark_mode"), "bob")
    assert evaluator.is_enabled("dark_mode", "alice") is False


# ── Cohorts ────────────────────────────────────────────────────


def test_user_in_cohort_returns_true(evaluator, redis_client, schema):
    """
    Given: flag allows cohort beta-testers. Alice belongs to beta-testers.
    Expected: is_enabled() returns True — cohort match found.
    """
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_cohorts("dark_mode"), "beta-testers")
    redis_client.sadd(schema.user_cohorts("alice"), "beta-testers")
    assert evaluator.is_enabled("dark_mode", "alice") is True


def test_user_not_in_cohort_returns_false(evaluator, redis_client, schema):
    """
    Given: flag allows cohort beta-testers. Alice belongs to premium-users only.
    Expected: is_enabled() returns False — no cohort match.
    """
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_cohorts("dark_mode"), "beta-testers")
    redis_client.sadd(schema.user_cohorts("alice"), "premium-users")
    assert evaluator.is_enabled("dark_mode", "alice") is False


def test_user_in_one_of_multiple_cohorts_returns_true(evaluator, redis_client, schema):
    """
    Given: flag allows beta-testers and internal cohorts. Alice belongs to internal only.
    Expected: is_enabled() returns True — one cohort match is enough.
    """
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_cohorts("dark_mode"), "beta-testers", "internal")
    redis_client.sadd(schema.user_cohorts("alice"), "internal")
    assert evaluator.is_enabled("dark_mode", "alice") is True


# ── Rollout ────────────────────────────────────────────────────


def test_rollout_100_returns_true(evaluator, redis_client, schema):
    """
    Given: flag with rollout=100.
    Expected: is_enabled() returns True — every user is in a 100% rollout.
    """
    create_flag(redis_client, schema, "dark_mode", rollout="100")
    assert evaluator.is_enabled("dark_mode", "alice") is True


def test_rollout_0_returns_false(evaluator, redis_client, schema):
    """
    Given: flag with rollout=0.
    Expected: is_enabled() returns False — nobody is in a 0% rollout.
    """
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    assert evaluator.is_enabled("dark_mode", "alice") is False


def test_rollout_deterministic(evaluator, redis_client, schema):
    """
    Given: flag with rollout=50. Same user evaluated twice.
    Expected: both calls return the same result — rollout is deterministic per user.
    """
    create_flag(redis_client, schema, "dark_mode", rollout="50")
    assert evaluator.is_enabled("dark_mode", "alice") == evaluator.is_enabled("dark_mode", "alice")


# ── Evaluation priority order ──────────────────────────────────


def test_allowlist_takes_priority_over_rollout(evaluator, redis_client, schema):
    """
    Given: flag with rollout=0 — would normally return False.
           Alice is in the user allowlist.
    Expected: is_enabled() returns True — allowlist checked before rollout.
    """
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_users("dark_mode"), "alice")
    assert evaluator.is_enabled("dark_mode", "alice") is True


def test_disabled_overrides_allowlist(evaluator, redis_client, schema):
    """
    Given: flag is disabled. Alice is in the allowlist and rollout=100.
    Expected: is_enabled() returns False — kill switch checked first, overrides everything.
    """
    create_flag(redis_client, schema, "dark_mode", enabled="0", rollout="100")
    redis_client.sadd(schema.flag_users("dark_mode"), "alice")
    assert evaluator.is_enabled("dark_mode", "alice") is False


# ── Cache ──────────────────────────────────────────────────────


def test_result_served_from_cache_on_second_call(evaluator, redis_client, schema, cache):
    """
    Given: flag evaluated once — populates local cache.
           Flag then deleted from Redis.
    Expected: second is_enabled() still returns True — served from cache.
    """
    create_flag(redis_client, schema, "dark_mode", rollout="100")
    evaluator.is_enabled("dark_mode", "alice")
    redis_client.delete(schema.flag("dark_mode"))
    assert evaluator.is_enabled("dark_mode", "alice") is True


def test_redis_down_serves_stale_cache(schema, cache):
    """
    Given: flag pre-loaded into cache. Redis then goes down.
    Expected: is_enabled() still returns True — stale cache used as fallback.
    """
    broken = fakeredis.FakeRedis()
    flag_key = schema.flag("dark_mode")
    cache.set(flag_key, {"enabled": "1", "rollout": "100", "expires_at": "0"})
    evaluator = Evaluator(broken, schema, cache)
    broken.close()
    assert evaluator.is_enabled("dark_mode", "alice", default=False) is True


# ── Redis error handling ───────────────────────────────────────


def test_user_in_allowlist_redis_error(schema, cache):
    """
    Given: flag in cache. Redis SISMEMBER throws an error.
    Expected: is_enabled() returns False — allowlist check fails safely.
    """
    from unittest.mock import patch
    client = fakeredis.FakeRedis()
    evaluator = Evaluator(client, schema, cache)
    cache.set(schema.flag("dark_mode"), {"enabled": "1", "rollout": "0", "expires_at": "0"})
    with patch.object(client, "sismember", side_effect=redis.RedisError("down")):
        assert evaluator.is_enabled("dark_mode", "alice") is False


def test_user_in_cohort_redis_error(schema, cache):
    """
    Given: flag in cache. Redis SINTER throws an error.
    Expected: is_enabled() returns False — cohort check fails safely.
    """
    from unittest.mock import patch
    client = fakeredis.FakeRedis()
    evaluator = Evaluator(client, schema, cache)
    cache.set(schema.flag("dark_mode"), {"enabled": "1", "rollout": "0", "expires_at": "0"})
    with patch.object(client, "sinter", side_effect=redis.RedisError("down")):
        assert evaluator.is_enabled("dark_mode", "alice") is False


def test_load_flag_redis_error_no_stale_cache(schema):
    """
    Given: flag never cached. Redis HGETALL throws an error.
    Expected: is_enabled() returns False (the default) — nothing to fall back to.
    """
    from unittest.mock import patch
    client = fakeredis.FakeRedis()
    cache = LocalCache()
    evaluator = Evaluator(client, schema, cache)
    with patch.object(client, "hgetall", side_effect=redis.RedisError("down")):
        assert evaluator.is_enabled("dark_mode", "alice", default=False) is False


def test_load_flag_redis_error_returns_stale(schema):
    """
    Given: flag in cache but TTL expired (cached_at=0). Redis HGETALL throws an error.
    Expected: is_enabled() returns True — stale cache used even though expired.
    """
    from unittest.mock import patch
    client = fakeredis.FakeRedis()
    cache = LocalCache()
    flag_key = schema.flag("dark_mode")
    cache.set(flag_key, {"enabled": "1", "rollout": "100", "expires_at": "0"})
    cache._store[flag_key].cached_at = 0
    evaluator = Evaluator(client, schema, cache)
    with patch.object(client, "hgetall", side_effect=redis.RedisError("down")):
        assert evaluator.is_enabled("dark_mode", "alice", default=False) is True


def test_user_in_cohort_returns_false_when_no_intersection(evaluator, redis_client, schema):
    """
    Given: flag has cohorts. Redis SINTER returns empty set — no cohort overlap.
    Expected: is_enabled() returns False — user is not in any allowed cohort.
    """
    from unittest.mock import patch
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    with patch.object(redis_client, "sinter", return_value=set()):
        assert evaluator.is_enabled("dark_mode", "alice") is False


def test_load_flag_redis_error_returns_stale_v2(schema):
    """
    Given: flag in cache but very old (cached 9999 seconds ago). Redis HGETALL throws error.
    Expected: is_enabled() returns True — get_stale() serves old data as last resort.
    """
    from unittest.mock import patch
    import time
    client = fakeredis.FakeRedis()
    cache = LocalCache()
    flag_key = schema.flag("dark_mode")
    cache.set(flag_key, {"enabled": "1", "rollout": "100", "expires_at": "0"})
    cache._store[flag_key].cached_at = time.monotonic() - 9999
    evaluator = Evaluator(client, schema, cache)
    with patch.object(client, "hgetall", side_effect=redis.RedisError("down")):
        assert evaluator.is_enabled("dark_mode", "alice", default=False) is True