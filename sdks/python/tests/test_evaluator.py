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
    defaults = {"enabled": "1", "rollout": "0", "expires_at": "0", "flag_version": "1"}
    defaults.update(kwargs)
    redis_client.hset(schema.flag(flag_name), mapping=defaults)


def test_missing_flag_returns_default_false(evaluator):
    assert evaluator.is_enabled("nonexistent", "alice") is False

def test_missing_flag_returns_custom_default(evaluator):
    assert evaluator.is_enabled("nonexistent", "alice", default=True) is True

def test_disabled_flag_returns_false(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", enabled="0", rollout="100")
    assert evaluator.is_enabled("dark_mode", "alice") is False

def test_enabled_flag_with_zero_rollout_returns_false(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", enabled="1", rollout="0")
    assert evaluator.is_enabled("dark_mode", "alice") is False

def test_expired_flag_returns_false(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", enabled="1", rollout="100", expires_at="1000")
    assert evaluator.is_enabled("dark_mode", "alice") is False

def test_future_expiry_does_not_block(evaluator, redis_client, schema):
    from redis_feature_flags.utils import now_unix
    future = str(now_unix() + 86400)
    create_flag(redis_client, schema, "dark_mode", enabled="1", rollout="100", expires_at=future)
    assert evaluator.is_enabled("dark_mode", "alice") is True

def test_no_expiry_zero_does_not_block(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", enabled="1", rollout="100", expires_at="0")
    assert evaluator.is_enabled("dark_mode", "alice") is True

def test_user_in_allowlist_returns_true(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_users("dark_mode"), "alice")
    assert evaluator.is_enabled("dark_mode", "alice") is True

def test_user_not_in_allowlist_continues_to_rollout(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_users("dark_mode"), "bob")
    assert evaluator.is_enabled("dark_mode", "alice") is False

def test_user_in_cohort_returns_true(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_cohorts("dark_mode"), "beta-testers")
    redis_client.sadd(schema.user_cohorts("alice"), "beta-testers")
    assert evaluator.is_enabled("dark_mode", "alice") is True

def test_user_not_in_cohort_returns_false(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_cohorts("dark_mode"), "beta-testers")
    redis_client.sadd(schema.user_cohorts("alice"), "premium-users")
    assert evaluator.is_enabled("dark_mode", "alice") is False

def test_user_in_one_of_multiple_cohorts_returns_true(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_cohorts("dark_mode"), "beta-testers", "internal")
    redis_client.sadd(schema.user_cohorts("alice"), "internal")
    assert evaluator.is_enabled("dark_mode", "alice") is True

def test_rollout_100_returns_true(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", rollout="100")
    assert evaluator.is_enabled("dark_mode", "alice") is True

def test_rollout_0_returns_false(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    assert evaluator.is_enabled("dark_mode", "alice") is False

def test_rollout_deterministic(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", rollout="50")
    assert evaluator.is_enabled("dark_mode", "alice") == evaluator.is_enabled("dark_mode", "alice")

def test_allowlist_takes_priority_over_rollout(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    redis_client.sadd(schema.flag_users("dark_mode"), "alice")
    assert evaluator.is_enabled("dark_mode", "alice") is True

def test_disabled_overrides_allowlist(evaluator, redis_client, schema):
    create_flag(redis_client, schema, "dark_mode", enabled="0", rollout="100")
    redis_client.sadd(schema.flag_users("dark_mode"), "alice")
    assert evaluator.is_enabled("dark_mode", "alice") is False

def test_result_served_from_cache_on_second_call(evaluator, redis_client, schema, cache):
    create_flag(redis_client, schema, "dark_mode", rollout="100")
    evaluator.is_enabled("dark_mode", "alice")
    redis_client.delete(schema.flag("dark_mode"))
    assert evaluator.is_enabled("dark_mode", "alice") is True

def test_redis_down_serves_stale_cache(schema, cache):
    broken = fakeredis.FakeRedis()
    flag_key = schema.flag("dark_mode")
    cache.set(flag_key, {"enabled": "1", "rollout": "100", "expires_at": "0"})
    evaluator = Evaluator(broken, schema, cache)
    broken.close()
    assert evaluator.is_enabled("dark_mode", "alice", default=False) is True

def test_user_in_allowlist_redis_error(schema, cache):
    from unittest.mock import patch
    client = fakeredis.FakeRedis()
    evaluator = Evaluator(client, schema, cache)
    cache.set(schema.flag("dark_mode"), {"enabled": "1", "rollout": "0", "expires_at": "0"})
    with patch.object(client, "sismember", side_effect=redis.RedisError("down")):
        assert evaluator.is_enabled("dark_mode", "alice") is False

def test_user_in_cohort_redis_error(schema, cache):
    from unittest.mock import patch
    client = fakeredis.FakeRedis()
    evaluator = Evaluator(client, schema, cache)
    cache.set(schema.flag("dark_mode"), {"enabled": "1", "rollout": "0", "expires_at": "0"})
    with patch.object(client, "sinter", side_effect=redis.RedisError("down")):
        assert evaluator.is_enabled("dark_mode", "alice") is False

def test_load_flag_redis_error_no_stale_cache(schema):
    from unittest.mock import patch
    client = fakeredis.FakeRedis()
    cache = LocalCache()
    evaluator = Evaluator(client, schema, cache)
    with patch.object(client, "hgetall", side_effect=redis.RedisError("down")):
        assert evaluator.is_enabled("dark_mode", "alice", default=False) is False

def test_load_flag_redis_error_returns_stale(schema):
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
    from unittest.mock import patch
    create_flag(redis_client, schema, "dark_mode", rollout="0")
    with patch.object(redis_client, "sinter", return_value=set()):
        assert evaluator.is_enabled("dark_mode", "alice") is False

def test_load_flag_redis_error_returns_stale_v2(schema):
    from unittest.mock import patch
    client = fakeredis.FakeRedis()
    cache = LocalCache()
    flag_key = schema.flag("dark_mode")
    cache.set(flag_key, {"enabled": "1", "rollout": "100", "expires_at": "0"})
    import time
    cache._store[flag_key].cached_at = time.monotonic() - 9999
    evaluator = Evaluator(client, schema, cache)
    with patch.object(client, "hgetall", side_effect=redis.RedisError("down")):
        result = evaluator.is_enabled("dark_mode", "alice", default=False)
    assert result is True