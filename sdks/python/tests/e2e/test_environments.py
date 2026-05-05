# sdks/python/tests/e2e/test_environments.py

"""
E2e tests — environment isolation against real Redis.

Two environments on the same Redis instance must not share any data:
flags, allowlists, cohorts, and index keys are all scoped per-env.
"""

from __future__ import annotations

import pytest

from redis_feature_flags import FeatureFlags
from redis_feature_flags.schema import SchemaKeys

from .constants import E2E_REDIS_PORT, E2E_ENV

# Two isolated sub-environments derived from the e2etest namespace
ENV_A = f"{E2E_ENV}_a"
ENV_B = f"{E2E_ENV}_b"


@pytest.fixture
def flags_a(redis_client):
    return FeatureFlags(redis_client, env=ENV_A)


@pytest.fixture
def flags_b(redis_client):
    return FeatureFlags(redis_client, env=ENV_B)


@pytest.fixture
def schema_a():
    return SchemaKeys(env=ENV_A)


@pytest.fixture
def schema_b():
    return SchemaKeys(env=ENV_B)


@pytest.fixture(autouse=True)
def clean_env_keys(redis_client):
    """Clean ENV_A and ENV_B keys before and after each test."""
    def flush():
        for env in (ENV_A, ENV_B):
            keys = redis_client.keys(f"ff:{env}:*")
            if keys:
                redis_client.delete(*keys)
    flush()
    yield
    flush()


# ── Flag isolation ─────────────────────────────────────────────


def test_flag_in_env_a_not_visible_in_env_b(flags_a, flags_b):
    flags_a.create("dark_mode", rollout=100)
    flags_a.enable("dark_mode")
    assert flags_a.is_enabled("dark_mode", user_id="alice") is True
    assert flags_b.is_enabled("dark_mode", user_id="alice") is False


def test_flag_in_env_b_not_visible_in_env_a(flags_a, flags_b):
    flags_b.create("dark_mode", rollout=100)
    flags_b.enable("dark_mode")
    assert flags_b.is_enabled("dark_mode", user_id="alice") is True
    assert flags_a.is_enabled("dark_mode", user_id="alice") is False


def test_list_flags_does_not_leak_across_envs(flags_a, flags_b):
    flags_a.create("flag_a_only")
    flags_b.create("flag_b_only")
    result_a = flags_a.list_flags()
    result_b = flags_b.list_flags()
    assert "flag_a_only" in result_a
    assert "flag_b_only" not in result_a
    assert "flag_b_only" in result_b
    assert "flag_a_only" not in result_b


def test_enable_in_env_a_does_not_affect_env_b(flags_a, flags_b):
    flags_a.create("dark_mode", rollout=100)
    flags_b.create("dark_mode", rollout=100)
    flags_a.enable("dark_mode")
    assert flags_a.is_enabled("dark_mode", user_id="alice") is True
    assert flags_b.is_enabled("dark_mode", user_id="alice") is False


def test_rollout_change_in_env_a_does_not_affect_env_b(flags_a, flags_b):
    flags_a.create("dark_mode")
    flags_b.create("dark_mode")
    flags_a.enable("dark_mode")
    flags_b.enable("dark_mode")
    flags_a.set_rollout("dark_mode", 100)
    flags_b.set_rollout("dark_mode", 0)
    assert flags_a.is_enabled("dark_mode", user_id="alice") is True
    assert flags_b.is_enabled("dark_mode", user_id="alice") is False


def test_delete_in_env_a_does_not_remove_flag_in_env_b(flags_a, flags_b):
    flags_a.create("dark_mode", rollout=100)
    flags_b.create("dark_mode", rollout=100)
    flags_a.enable("dark_mode")
    flags_b.enable("dark_mode")
    flags_a.delete("dark_mode")
    assert flags_a.is_enabled("dark_mode", user_id="alice") is False
    assert flags_b.is_enabled("dark_mode", user_id="alice") is True


def test_same_flag_name_can_exist_independently_in_both_envs(flags_a, flags_b, schema_a, schema_b, redis_client):
    flags_a.create("dark_mode", rollout=10, created_by="alice")
    flags_b.create("dark_mode", rollout=50, created_by="bob")
    data_a = redis_client.hgetall(schema_a.flag("dark_mode"))
    data_b = redis_client.hgetall(schema_b.flag("dark_mode"))
    assert data_a[b"rollout"] == b"10"
    assert data_b[b"rollout"] == b"50"
    assert data_a[b"created_by"] == b"alice"
    assert data_b[b"created_by"] == b"bob"


# ── Allowlist isolation ────────────────────────────────────────


def test_allowlist_is_scoped_to_environment(flags_a, flags_b):
    flags_a.create("dark_mode", rollout=0)
    flags_b.create("dark_mode", rollout=0)
    flags_a.enable("dark_mode")
    flags_b.enable("dark_mode")
    flags_a.add_user("dark_mode", "alice")
    assert flags_a.is_enabled("dark_mode", user_id="alice") is True
    assert flags_b.is_enabled("dark_mode", user_id="alice") is False


# ── Cohort isolation ───────────────────────────────────────────


def test_cohort_membership_is_scoped_to_environment(flags_a, flags_b):
    flags_a.create("dark_mode", rollout=0)
    flags_b.create("dark_mode", rollout=0)
    flags_a.enable("dark_mode")
    flags_b.enable("dark_mode")
    flags_a.create_cohort("beta")
    flags_a.add_to_cohort("beta", "alice")
    flags_a.add_cohort_to_flag("dark_mode", "beta")
    assert flags_a.is_enabled("dark_mode", user_id="alice") is True
    assert flags_b.is_enabled("dark_mode", user_id="alice") is False


def test_cohort_index_is_scoped_to_environment(flags_a, flags_b, schema_a, schema_b, redis_client):
    flags_a.create_cohort("beta")
    flags_b.create_cohort("gamma")
    cohorts_a = redis_client.smembers(schema_a.cohorts_index())
    cohorts_b = redis_client.smembers(schema_b.cohorts_index())
    assert b"beta" in cohorts_a
    assert b"gamma" not in cohorts_a
    assert b"gamma" in cohorts_b
    assert b"beta" not in cohorts_b


# ── Schema key isolation ───────────────────────────────────────


def test_flag_keys_have_distinct_env_prefix(schema_a, schema_b):
    assert schema_a.flag("dark_mode") == f"ff:{ENV_A}:flag:dark_mode"
    assert schema_b.flag("dark_mode") == f"ff:{ENV_B}:flag:dark_mode"
    assert schema_a.flag("dark_mode") != schema_b.flag("dark_mode")


def test_flags_index_keys_are_distinct_per_env(schema_a, schema_b):
    assert schema_a.flags_index() != schema_b.flags_index()
    assert ENV_A in schema_a.flags_index()
    assert ENV_B in schema_b.flags_index()


def test_cohorts_index_keys_are_distinct_per_env(schema_a, schema_b):
    assert schema_a.cohorts_index() != schema_b.cohorts_index()
    assert ENV_A in schema_a.cohorts_index()
    assert ENV_B in schema_b.cohorts_index()
