# sdks/python/tests/e2e/test_flag_lifecycle.py

"""
E2e tests — flag lifecycle against real Redis.

Tests the complete journey of a flag:
create → enable → disable → set_rollout → delete

Every test uses real Redis on port 6399.
Every test starts with a clean slate via conftest.py autouse fixture.
"""

from __future__ import annotations

import pytest
import redis as redis_lib

from redis_feature_flags import FeatureFlags
from redis_feature_flags.exceptions import FlagNotFoundError, InvalidRolloutError
from redis_feature_flags.schema import SchemaKeys

from .constants import E2E_ENV


# ── Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def flags(redis_client):
    """
    FeatureFlags instance connected to real Redis on port 6399.
    Uses e2etest environment — isolated from prod/staging/dev.
    """
    return FeatureFlags(redis_client, env=E2E_ENV)


@pytest.fixture
def schema():
    return SchemaKeys(env=E2E_ENV)


# ── Create ─────────────────────────────────────────────────────


def test_create_flag_exists_in_redis(flags, redis_client, schema):
    """
    Given: redis-feature-flags connected to real Redis.
    After: flags.create("dark_mode") called.
    Expected: flag Hash exists in real Redis with correct fields.
    """
    flags.create("dark_mode", rollout=10, created_by="alice")

    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"enabled"] == b"0"
    assert data[b"rollout"] == b"10"
    assert data[b"created_by"] == b"alice"
    assert data[b"flag_version"] == b"1"


def test_create_flag_appears_in_index(flags, redis_client, schema):
    """
    Given: flags.create("dark_mode") called.
    Expected: dark_mode appears in flags:__index__ Set in real Redis.
    """
    flags.create("dark_mode")
    members = redis_client.smembers(schema.flags_index())
    assert b"dark_mode" in members


def test_create_flag_disabled_by_default(flags):
    """
    Given: flags.create("dark_mode") called with no arguments.
    Expected: flag is disabled — is_enabled() returns False.
    """
    flags.create("dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_create_flag_invalid_rollout_raises(flags):
    """
    Given: flags.create() called with rollout=150.
    Expected: InvalidRolloutError raised — rollout must be 0-100.
    """
    with pytest.raises(InvalidRolloutError):
        flags.create("dark_mode", rollout=150)


def test_create_flag_invalid_rollout_negative_raises(flags):
    """
    Given: flags.create() called with rollout=-1.
    Expected: InvalidRolloutError raised.
    """
    with pytest.raises(InvalidRolloutError):
        flags.create("dark_mode", rollout=-1)


def test_create_multiple_flags(flags):
    """
    Given: three flags created.
    Expected: list_flags() returns all three names.
    """
    flags.create("dark_mode")
    flags.create("new_checkout")
    flags.create("ai_search")

    result = flags.list_flags()
    assert "dark_mode" in result
    assert "new_checkout" in result
    assert "ai_search" in result


# ── Enable ─────────────────────────────────────────────────────


def test_enable_flag_updates_redis(flags, redis_client, schema):
    """
    Given: dark_mode created and enabled.
    Expected: enabled field in real Redis is "1".
    """
    flags.create("dark_mode")
    flags.enable("dark_mode")

    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"enabled"] == b"1"


def test_enable_flag_updates_updated_by(flags, redis_client, schema):
    """
    Given: dark_mode enabled with updated_by=bob.
    Expected: updated_by field in real Redis is "bob".
    """
    flags.create("dark_mode")
    flags.enable("dark_mode", updated_by="bob")

    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"updated_by"] == b"bob"


def test_enable_nonexistent_flag_raises(flags):
    """
    Given: flag nonexistent does not exist.
    After: flags.enable("nonexistent") called.
    Expected: FlagNotFoundError raised.
    """
    with pytest.raises(FlagNotFoundError):
        flags.enable("nonexistent")


def test_enable_flag_is_enabled_returns_true(flags):
    """
    Given: dark_mode created, enabled, rollout=100.
    Expected: is_enabled() returns True for any user.
    """
    flags.create("dark_mode", rollout=100)
    flags.enable("dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is True


# ── Disable ────────────────────────────────────────────────────


def test_disable_flag_updates_redis(flags, redis_client, schema):
    """
    Given: dark_mode enabled then disabled.
    Expected: enabled field in real Redis is "0".
    """
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.disable("dark_mode")

    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"enabled"] == b"0"


def test_disable_flag_is_enabled_returns_false(flags):
    """
    Given: dark_mode enabled with rollout=100, then disabled.
    Expected: is_enabled() returns False — kill switch works.
    """
    flags.create("dark_mode", rollout=100)
    flags.enable("dark_mode")
    flags.disable("dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_disable_nonexistent_flag_raises(flags):
    """
    Given: flag nonexistent does not exist.
    After: flags.disable("nonexistent") called.
    Expected: FlagNotFoundError raised.
    """
    with pytest.raises(FlagNotFoundError):
        flags.disable("nonexistent")


# ── Set rollout ────────────────────────────────────────────────


def test_set_rollout_updates_redis(flags, redis_client, schema):
    """
    Given: dark_mode created, set_rollout(50) called.
    Expected: rollout field in real Redis is "50".
    """
    flags.create("dark_mode")
    flags.set_rollout("dark_mode", 50)

    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"rollout"] == b"50"


def test_set_rollout_zero_disables_rollout(flags):
    """
    Given: dark_mode enabled, rollout set to 0.
    Expected: is_enabled() returns False for all users
              unless they are in allowlist or cohort.
    """
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.set_rollout("dark_mode", 0)
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_set_rollout_hundred_enables_all(flags):
    """
    Given: dark_mode enabled, rollout set to 100.
    Expected: is_enabled() returns True for all users.
    """
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.set_rollout("dark_mode", 100)
    assert flags.is_enabled("dark_mode", user_id="alice") is True
    assert flags.is_enabled("dark_mode", user_id="bob") is True
    assert flags.is_enabled("dark_mode", user_id="charlie") is True


def test_set_rollout_invalid_raises(flags):
    """
    Given: dark_mode created, set_rollout(150) called.
    Expected: InvalidRolloutError raised.
    """
    flags.create("dark_mode")
    with pytest.raises(InvalidRolloutError):
        flags.set_rollout("dark_mode", 150)


def test_set_rollout_nonexistent_flag_raises(flags):
    """
    Given: flag nonexistent does not exist.
    After: flags.set_rollout("nonexistent", 50) called.
    Expected: FlagNotFoundError raised.
    """
    with pytest.raises(FlagNotFoundError):
        flags.set_rollout("nonexistent", 50)


# ── Get ────────────────────────────────────────────────────────


def test_get_flag_returns_correct_fields(flags):
    """
    Given: dark_mode created with rollout=10, created_by=alice.
    Expected: get() returns dict with all correct field values.
    """
    flags.create("dark_mode", rollout=10, created_by="alice")
    data = flags.get("dark_mode")

    assert data["enabled"] == "0"
    assert data["rollout"] == "10"
    assert data["created_by"] == "alice"
    assert data["flag_version"] == "1"


def test_get_nonexistent_flag_raises(flags):
    """
    Given: flag nonexistent does not exist.
    After: flags.get("nonexistent") called.
    Expected: FlagNotFoundError raised.
    """
    with pytest.raises(FlagNotFoundError):
        flags.get("nonexistent")


# ── Delete ─────────────────────────────────────────────────────


def test_delete_removes_flag_from_redis(flags, redis_client, schema):
    """
    Given: dark_mode created then deleted.
    Expected: flag Hash no longer exists in real Redis.
    """
    flags.create("dark_mode")
    flags.delete("dark_mode")

    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data == {}


def test_delete_removes_flag_from_index(flags, redis_client, schema):
    """
    Given: dark_mode created then deleted.
    Expected: dark_mode no longer in flags:__index__ Set.
    """
    flags.create("dark_mode")
    flags.delete("dark_mode")

    members = redis_client.smembers(schema.flags_index())
    assert b"dark_mode" not in members


def test_delete_removes_users_set(flags, redis_client, schema):
    """
    Given: dark_mode created, alice added to allowlist, flag deleted.
    Expected: users Set no longer exists in real Redis.
    """
    flags.create("dark_mode")
    flags.add_user("dark_mode", "alice")
    flags.delete("dark_mode")

    members = redis_client.smembers(schema.flag_users("dark_mode"))
    assert members == set()


def test_delete_removes_cohorts_set(flags, redis_client, schema):
    """
    Given: dark_mode created, cohort attached, flag deleted.
    Expected: flag cohorts Set no longer exists in real Redis.
    """
    flags.create("dark_mode")
    flags.create_cohort("beta-testers")
    flags.add_cohort_to_flag("dark_mode", "beta-testers")
    flags.delete("dark_mode")

    members = redis_client.smembers(schema.flag_cohorts("dark_mode"))
    assert members == set()


def test_delete_flag_is_enabled_returns_default(flags):
    """
    Given: dark_mode created, enabled, then deleted.
    Expected: is_enabled() returns False — flag is gone.
    """
    flags.create("dark_mode", rollout=100)
    flags.enable("dark_mode")
    flags.delete("dark_mode")

    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_delete_then_recreate(flags):
    """
    Given: dark_mode created, deleted, then recreated.
    Expected: new flag starts fresh — disabled, rollout 0.
    """
    flags.create("dark_mode", rollout=100)
    flags.enable("dark_mode")
    flags.delete("dark_mode")
    flags.create("dark_mode", rollout=0)

    assert flags.is_enabled("dark_mode", user_id="alice") is False


# ── List ───────────────────────────────────────────────────────


def test_list_flags_returns_all_created(flags):
    """
    Given: three flags created.
    Expected: list_flags() returns all three — no KEYS * scan.
    """
    flags.create("dark_mode")
    flags.create("new_checkout")
    flags.create("ai_search")

    result = flags.list_flags()
    assert "dark_mode" in result
    assert "new_checkout" in result
    assert "ai_search" in result


def test_list_flags_empty_when_none_created(flags):
    """
    Given: no flags created.
    Expected: list_flags() returns empty list.
    """
    assert flags.list_flags() == []


def test_list_flags_excludes_deleted(flags):
    """
    Given: dark_mode and new_checkout created, dark_mode deleted.
    Expected: list_flags() returns only new_checkout.
    """
    flags.create("dark_mode")
    flags.create("new_checkout")
    flags.delete("dark_mode")

    result = flags.list_flags()
    assert "dark_mode" not in result
    assert "new_checkout" in result


# ── User targeting ─────────────────────────────────────────────


def test_add_user_to_allowlist(flags, redis_client, schema):
    """
    Given: alice added to dark_mode allowlist.
    Expected: alice in flag_users Set in real Redis.
    """
    flags.create("dark_mode")
    flags.add_user("dark_mode", "alice")

    members = redis_client.smembers(schema.flag_users("dark_mode"))
    assert b"alice" in members


def test_remove_user_from_allowlist(flags, redis_client, schema):
    """
    Given: alice added then removed from dark_mode allowlist.
    Expected: alice not in flag_users Set in real Redis.
    """
    flags.create("dark_mode")
    flags.add_user("dark_mode", "alice")
    flags.remove_user("dark_mode", "alice")

    members = redis_client.smembers(schema.flag_users("dark_mode"))
    assert b"alice" not in members