# sdks/python/tests/e2e/test_evaluation.py

"""
E2e tests — flag evaluation engine against real Redis.

Covers all six evaluation steps:
  1. Flag exists
  2. Flag enabled
  3. Flag not expired
  4. User in allowlist
  5. User in cohort
  6. User in rollout
"""

from __future__ import annotations

import hashlib
import time

import pytest

from redis_feature_flags import FeatureFlags
from redis_feature_flags.schema import SchemaKeys

from .constants import E2E_ENV


def _bucket(flag_name: str, user_id: str) -> int:
    key = f"{flag_name}:{user_id}"
    hash_hex = hashlib.sha256(key.encode()).hexdigest()
    return int(hash_hex[:8], 16) % 100


@pytest.fixture
def flags(redis_client):
    return FeatureFlags(redis_client, env=E2E_ENV)


@pytest.fixture
def schema():
    return SchemaKeys(env=E2E_ENV)


# ── Step 1: flag exists ────────────────────────────────────────


def test_default_false_when_flag_missing(flags):
    assert flags.is_enabled("ghost_flag", user_id="alice") is False


def test_default_true_when_flag_missing(flags):
    assert flags.is_enabled("ghost_flag", user_id="alice", default=True) is True


# ── Step 2: kill switch ────────────────────────────────────────


def test_disabled_flag_returns_false(flags):
    flags.create("dark_mode", rollout=100)
    # not enabled — kill switch is off
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_enabled_flag_with_rollout_hundred(flags):
    flags.create("dark_mode", rollout=100)
    flags.enable("dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is True


# ── Step 3: expiry ─────────────────────────────────────────────


def test_expired_flag_returns_false(flags, redis_client, schema):
    flags.create("dark_mode", rollout=100)
    flags.enable("dark_mode")
    # Write an expires_at in the past directly
    past_ts = str(int(time.time()) - 1)
    redis_client.hset(schema.flag("dark_mode"), "expires_at", past_ts)
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_unexpired_flag_evaluates_normally(flags, redis_client, schema):
    flags.create("dark_mode", rollout=100)
    flags.enable("dark_mode")
    future_ts = str(int(time.time()) + 3600)
    redis_client.hset(schema.flag("dark_mode"), "expires_at", future_ts)
    assert flags.is_enabled("dark_mode", user_id="alice") is True


# ── Step 4: allowlist ──────────────────────────────────────────


def test_allowlist_bypasses_rollout_zero(flags):
    flags.create("dark_mode", rollout=0)
    flags.enable("dark_mode")
    flags.add_user("dark_mode", "alice")
    assert flags.is_enabled("dark_mode", user_id="alice") is True


def test_allowlist_does_not_affect_other_users(flags):
    flags.create("dark_mode", rollout=0)
    flags.enable("dark_mode")
    flags.add_user("dark_mode", "alice")
    assert flags.is_enabled("dark_mode", user_id="bob") is False


def test_removed_user_loses_allowlist_access(flags):
    flags.create("dark_mode", rollout=0)
    flags.enable("dark_mode")
    flags.add_user("dark_mode", "alice")
    flags.remove_user("dark_mode", "alice")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


# ── Step 5: cohort ─────────────────────────────────────────────


def test_cohort_member_bypasses_rollout_zero(flags):
    flags.create("dark_mode", rollout=0)
    flags.enable("dark_mode")
    flags.create_cohort("beta")
    flags.add_to_cohort("beta", "alice")
    flags.add_cohort_to_flag("dark_mode", "beta")
    assert flags.is_enabled("dark_mode", user_id="alice") is True


def test_non_cohort_member_blocked(flags):
    flags.create("dark_mode", rollout=0)
    flags.enable("dark_mode")
    flags.create_cohort("beta")
    flags.add_to_cohort("beta", "alice")
    flags.add_cohort_to_flag("dark_mode", "beta")
    assert flags.is_enabled("dark_mode", user_id="bob") is False


# ── Step 6: rollout ────────────────────────────────────────────


def test_rollout_zero_blocks_all(flags):
    flags.create("dark_mode", rollout=0)
    flags.enable("dark_mode")
    for uid in ("alice", "bob", "charlie", "dave", "eve"):
        assert flags.is_enabled("dark_mode", user_id=uid) is False


def test_rollout_hundred_allows_all(flags):
    flags.create("dark_mode", rollout=100)
    flags.enable("dark_mode")
    for uid in ("alice", "bob", "charlie", "dave", "eve"):
        assert flags.is_enabled("dark_mode", user_id=uid) is True


def test_rollout_deterministic_in(flags):
    """User whose bucket < rollout is always in."""
    user = "alice"
    bucket = _bucket("dark_mode", user)
    flags.create("dark_mode", rollout=bucket + 1)
    flags.enable("dark_mode")
    assert flags.is_enabled("dark_mode", user_id=user) is True


def test_rollout_deterministic_out(flags):
    """User whose bucket == rollout is always out."""
    user = "alice"
    bucket = _bucket("dark_mode", user)
    flags.create("dark_mode", rollout=bucket)
    flags.enable("dark_mode")
    assert flags.is_enabled("dark_mode", user_id=user) is False
