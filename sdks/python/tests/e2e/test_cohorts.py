# sdks/python/tests/e2e/test_cohorts.py

"""
E2e tests — cohort management against real Redis.

Covers:
  - Create, list cohorts
  - Add/remove users with bidirectional index consistency
  - Delete cohort cleanup
  - Cohort targeting on flags
  - Multiple cohorts per flag and per user
"""

from __future__ import annotations

import pytest

from redis_feature_flags import FeatureFlags
from redis_feature_flags.schema import SchemaKeys

from .constants import E2E_ENV


@pytest.fixture
def flags(redis_client):
    return FeatureFlags(redis_client, env=E2E_ENV)


@pytest.fixture
def schema():
    return SchemaKeys(env=E2E_ENV)


# ── Create ─────────────────────────────────────────────────────


def test_create_cohort_appears_in_index(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    members = redis_client.smembers(schema.cohorts_index())
    assert b"beta-testers" in members


def test_create_multiple_cohorts_all_in_index(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.create_cohort("premium-users")
    flags.create_cohort("internal")
    members = redis_client.smembers(schema.cohorts_index())
    assert b"beta-testers" in members
    assert b"premium-users" in members
    assert b"internal" in members


def test_create_cohort_starts_empty(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    members = redis_client.smembers(schema.cohort("beta-testers"))
    assert members == set()


# ── Add / remove users ─────────────────────────────────────────


def test_add_user_appears_in_cohort_members(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    members = redis_client.smembers(schema.cohort("beta-testers"))
    assert b"alice" in members


def test_add_user_updates_reverse_index(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    user_cohorts = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" in user_cohorts


def test_remove_user_leaves_cohort_members(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.remove_from_cohort("beta-testers", "alice")
    members = redis_client.smembers(schema.cohort("beta-testers"))
    assert b"alice" not in members


def test_remove_user_cleans_reverse_index(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.remove_from_cohort("beta-testers", "alice")
    user_cohorts = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" not in user_cohorts


def test_user_in_multiple_cohorts_both_recorded(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.create_cohort("premium-users")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_to_cohort("premium-users", "alice")
    user_cohorts = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" in user_cohorts
    assert b"premium-users" in user_cohorts


def test_multiple_users_in_same_cohort(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_to_cohort("beta-testers", "bob")
    flags.add_to_cohort("beta-testers", "charlie")
    members = redis_client.smembers(schema.cohort("beta-testers"))
    assert b"alice" in members
    assert b"bob" in members
    assert b"charlie" in members


# ── Delete cohort ──────────────────────────────────────────────


def test_delete_cohort_removes_from_index(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.create_cohort("premium-users")
    flags._cohorts.delete("beta-testers")
    members = redis_client.smembers(schema.cohorts_index())
    assert b"beta-testers" not in members
    assert b"premium-users" in members


def test_delete_cohort_removes_all_members(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_to_cohort("beta-testers", "bob")
    flags._cohorts.delete("beta-testers")
    members = redis_client.smembers(schema.cohort("beta-testers"))
    assert members == set()


def test_delete_cohort_cleans_user_reverse_index(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags._cohorts.delete("beta-testers")
    user_cohorts = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" not in user_cohorts


def test_delete_cohort_cleans_all_members_reverse_index(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_to_cohort("beta-testers", "bob")
    flags.add_to_cohort("beta-testers", "charlie")
    flags._cohorts.delete("beta-testers")
    for user in ("alice", "bob", "charlie"):
        user_cohorts = redis_client.smembers(schema.user_cohorts(user))
        assert b"beta-testers" not in user_cohorts


def test_delete_cohort_preserves_other_cohort_in_reverse_index(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags.create_cohort("premium-users")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_to_cohort("premium-users", "alice")
    flags._cohorts.delete("beta-testers")
    user_cohorts = redis_client.smembers(schema.user_cohorts("alice"))
    assert b"beta-testers" not in user_cohorts
    assert b"premium-users" in user_cohorts


def test_delete_empty_cohort_no_error(flags, redis_client, schema):
    flags.create_cohort("beta-testers")
    flags._cohorts.delete("beta-testers")
    members = redis_client.smembers(schema.cohorts_index())
    assert b"beta-testers" not in members


# ── Cohort targeting on flags ──────────────────────────────────


def test_add_cohort_to_flag_recorded_in_redis(flags, redis_client, schema):
    flags.create("dark_mode", rollout=0)
    flags.create_cohort("beta-testers")
    flags.add_cohort_to_flag("dark_mode", "beta-testers")
    flag_cohorts = redis_client.smembers(schema.flag_cohorts("dark_mode"))
    assert b"beta-testers" in flag_cohorts


def test_remove_cohort_from_flag_cleaned_in_redis(flags, redis_client, schema):
    flags.create("dark_mode", rollout=0)
    flags.create_cohort("beta-testers")
    flags.add_cohort_to_flag("dark_mode", "beta-testers")
    flags.remove_cohort_from_flag("dark_mode", "beta-testers")
    flag_cohorts = redis_client.smembers(schema.flag_cohorts("dark_mode"))
    assert b"beta-testers" not in flag_cohorts


def test_multiple_cohorts_on_flag_each_member_gets_access(flags):
    flags.create("dark_mode", rollout=0)
    flags.enable("dark_mode")
    flags.create_cohort("beta-testers")
    flags.create_cohort("internal")
    flags.add_cohort_to_flag("dark_mode", "beta-testers")
    flags.add_cohort_to_flag("dark_mode", "internal")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_to_cohort("internal", "bob")
    assert flags.is_enabled("dark_mode", user_id="alice") is True
    assert flags.is_enabled("dark_mode", user_id="bob") is True
    assert flags.is_enabled("dark_mode", user_id="charlie") is False


def test_cohort_targeting_revoked_when_user_removed(flags):
    flags.create("dark_mode", rollout=0)
    flags.enable("dark_mode")
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_cohort_to_flag("dark_mode", "beta-testers")
    assert flags.is_enabled("dark_mode", user_id="alice") is True
    flags.remove_from_cohort("beta-testers", "alice")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_cohort_targeting_revoked_when_cohort_removed_from_flag(flags):
    flags.create("dark_mode", rollout=0)
    flags.enable("dark_mode")
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_cohort_to_flag("dark_mode", "beta-testers")
    assert flags.is_enabled("dark_mode", user_id="alice") is True
    flags.remove_cohort_from_flag("dark_mode", "beta-testers")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_user_in_cohort_not_linked_to_flag_gets_no_access(flags):
    flags.create("dark_mode", rollout=0)
    flags.enable("dark_mode")
    flags.create_cohort("beta-testers")
    flags.create_cohort("other")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_cohort_to_flag("dark_mode", "other")
    assert flags.is_enabled("dark_mode", user_id="alice") is False
