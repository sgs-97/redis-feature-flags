# sdks/python/tests/e2e/test_cli.py

"""
E2e tests — CLI commands against real Redis.

Uses typer's CliRunner to invoke the redis-flags CLI
against a real Redis instance on port 6399.

Every test uses --env e2etest and --redis-url redis://localhost:6399
so keys land in the e2etest namespace and are cleaned by conftest.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from redis_flags.main import app
from redis_feature_flags import FeatureFlags

from .constants import E2E_ENV, E2E_REDIS_URL


@pytest.fixture
def runner():
    return CliRunner()


# Shared CLI args injected into every command
ENV_ARGS = ["--env", E2E_ENV, "--redis-url", E2E_REDIS_URL]


def invoke(runner, *args):
    """Invoke CLI with env + redis-url args automatically appended."""
    return runner.invoke(app, list(args) + ENV_ARGS)


# ── create ─────────────────────────────────────────────────────


def test_create_flag_exits_zero(runner):
    result = invoke(runner, "create", "dark_mode")
    assert result.exit_code == 0


def test_create_flag_success_message(runner):
    result = invoke(runner, "create", "dark_mode")
    assert "dark_mode" in result.output


def test_create_flag_with_rollout(runner, redis_client):
    invoke(runner, "create", "dark_mode", "--rollout", "25")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"rollout"] == b"25"


def test_create_flag_with_created_by(runner, redis_client):
    invoke(runner, "create", "dark_mode", "--created-by", "alice")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"created_by"] == b"alice"


def test_create_flag_disabled_by_default(runner, redis_client):
    invoke(runner, "create", "dark_mode")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"enabled"] == b"0"


def test_create_flag_invalid_rollout_exits_nonzero(runner):
    result = invoke(runner, "create", "dark_mode", "--rollout", "150")
    assert result.exit_code != 0


# ── enable ─────────────────────────────────────────────────────


def test_enable_flag_exits_zero(runner):
    invoke(runner, "create", "dark_mode")
    result = invoke(runner, "enable", "dark_mode")
    assert result.exit_code == 0


def test_enable_flag_success_message(runner):
    invoke(runner, "create", "dark_mode")
    result = invoke(runner, "enable", "dark_mode")
    assert "dark_mode" in result.output


def test_enable_flag_sets_enabled_in_redis(runner, redis_client):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "enable", "dark_mode")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"enabled"] == b"1"


def test_enable_nonexistent_flag_exits_nonzero(runner):
    result = invoke(runner, "enable", "ghost_flag")
    assert result.exit_code != 0


# ── disable ────────────────────────────────────────────────────


def test_disable_flag_exits_zero(runner):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "enable", "dark_mode")
    result = invoke(runner, "disable", "dark_mode")
    assert result.exit_code == 0


def test_disable_flag_sets_enabled_zero_in_redis(runner, redis_client):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "enable", "dark_mode")
    invoke(runner, "disable", "dark_mode")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"enabled"] == b"0"


def test_disable_nonexistent_flag_exits_nonzero(runner):
    result = invoke(runner, "disable", "ghost_flag")
    assert result.exit_code != 0


# ── set-rollout ────────────────────────────────────────────────


def test_set_rollout_exits_zero(runner):
    invoke(runner, "create", "dark_mode")
    result = invoke(runner, "set-rollout", "dark_mode", "50")
    assert result.exit_code == 0


def test_set_rollout_updates_redis(runner, redis_client):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "set-rollout", "dark_mode", "75")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data[b"rollout"] == b"75"


def test_set_rollout_invalid_value_exits_nonzero(runner):
    invoke(runner, "create", "dark_mode")
    result = invoke(runner, "set-rollout", "dark_mode", "200")
    assert result.exit_code != 0


def test_set_rollout_nonexistent_flag_exits_nonzero(runner):
    result = invoke(runner, "set-rollout", "ghost_flag", "50")
    assert result.exit_code != 0


# ── delete ─────────────────────────────────────────────────────


def test_delete_flag_exits_zero(runner):
    invoke(runner, "create", "dark_mode")
    result = invoke(runner, "delete", "dark_mode", "--yes")
    assert result.exit_code == 0


def test_delete_flag_removes_from_redis(runner, redis_client):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "delete", "dark_mode", "--yes")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    data = redis_client.hgetall(schema.flag("dark_mode"))
    assert data == {}


def test_delete_flag_removes_from_index(runner, redis_client):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "delete", "dark_mode", "--yes")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    members = redis_client.smembers(schema.flags_index())
    assert b"dark_mode" not in members


# ── list ───────────────────────────────────────────────────────


def test_list_flags_exits_zero(runner):
    result = invoke(runner, "list")
    assert result.exit_code == 0


def test_list_flags_shows_created_flag(runner):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "create", "new_checkout")
    result = invoke(runner, "list")
    assert "dark_mode" in result.output
    assert "new_checkout" in result.output


def test_list_flags_empty_no_error(runner):
    result = invoke(runner, "list")
    assert result.exit_code == 0


# ── inspect ────────────────────────────────────────────────────


def test_inspect_flag_exits_zero(runner):
    invoke(runner, "create", "dark_mode")
    result = invoke(runner, "inspect", "dark_mode")
    assert result.exit_code == 0


def test_inspect_flag_shows_flag_name(runner):
    invoke(runner, "create", "dark_mode", "--rollout", "20")
    result = invoke(runner, "inspect", "dark_mode")
    assert "dark_mode" in result.output


def test_inspect_nonexistent_flag_exits_nonzero(runner):
    result = invoke(runner, "inspect", "ghost_flag")
    assert result.exit_code != 0


# ── add-user / remove-user ─────────────────────────────────────


def test_add_user_exits_zero(runner):
    invoke(runner, "create", "dark_mode")
    result = invoke(runner, "add-user", "dark_mode", "alice")
    assert result.exit_code == 0


def test_add_user_appears_in_allowlist(runner, redis_client):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "add-user", "dark_mode", "alice")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    members = redis_client.smembers(schema.flag_users("dark_mode"))
    assert b"alice" in members


def test_add_user_nonexistent_flag_exits_nonzero(runner):
    result = invoke(runner, "add-user", "ghost_flag", "alice")
    assert result.exit_code != 0


def test_remove_user_exits_zero(runner):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "add-user", "dark_mode", "alice")
    result = invoke(runner, "remove-user", "dark_mode", "alice")
    assert result.exit_code == 0


def test_remove_user_leaves_allowlist(runner, redis_client):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "add-user", "dark_mode", "alice")
    invoke(runner, "remove-user", "dark_mode", "alice")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    members = redis_client.smembers(schema.flag_users("dark_mode"))
    assert b"alice" not in members


# ── create-cohort / delete-cohort ──────────────────────────────


def test_create_cohort_exits_zero(runner):
    result = invoke(runner, "create-cohort", "beta-testers")
    assert result.exit_code == 0


def test_create_cohort_appears_in_redis(runner, redis_client):
    invoke(runner, "create-cohort", "beta-testers")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    members = redis_client.smembers(schema.cohorts_index())
    assert b"beta-testers" in members


def test_delete_cohort_exits_zero(runner):
    invoke(runner, "create-cohort", "beta-testers")
    result = invoke(runner, "delete-cohort", "beta-testers", "--yes")
    assert result.exit_code == 0


def test_delete_cohort_removes_from_redis(runner, redis_client):
    invoke(runner, "create-cohort", "beta-testers")
    invoke(runner, "delete-cohort", "beta-testers", "--yes")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    members = redis_client.smembers(schema.cohorts_index())
    assert b"beta-testers" not in members


# ── add-to-cohort / remove-from-cohort ────────────────────────


def test_add_to_cohort_exits_zero(runner):
    invoke(runner, "create-cohort", "beta-testers")
    result = invoke(runner, "add-to-cohort", "beta-testers", "alice")
    assert result.exit_code == 0


def test_add_to_cohort_updates_redis(runner, redis_client):
    invoke(runner, "create-cohort", "beta-testers")
    invoke(runner, "add-to-cohort", "beta-testers", "alice")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    members = redis_client.smembers(schema.cohort("beta-testers"))
    assert b"alice" in members


def test_remove_from_cohort_exits_zero(runner):
    invoke(runner, "create-cohort", "beta-testers")
    invoke(runner, "add-to-cohort", "beta-testers", "alice")
    result = invoke(runner, "remove-from-cohort", "beta-testers", "alice")
    assert result.exit_code == 0


def test_remove_from_cohort_updates_redis(runner, redis_client):
    invoke(runner, "create-cohort", "beta-testers")
    invoke(runner, "add-to-cohort", "beta-testers", "alice")
    invoke(runner, "remove-from-cohort", "beta-testers", "alice")
    from redis_feature_flags.schema import SchemaKeys
    schema = SchemaKeys(env=E2E_ENV)
    members = redis_client.smembers(schema.cohort("beta-testers"))
    assert b"alice" not in members


# ── list-cohorts ───────────────────────────────────────────────


def test_list_cohorts_exits_zero(runner):
    result = invoke(runner, "list-cohorts")
    assert result.exit_code == 0


def test_list_cohorts_shows_created_cohort(runner):
    invoke(runner, "create-cohort", "beta-testers")
    result = invoke(runner, "list-cohorts")
    assert "beta-testers" in result.output


# ── inspect-cohort ─────────────────────────────────────────────


def test_inspect_cohort_exits_zero(runner):
    invoke(runner, "create-cohort", "beta-testers")
    result = invoke(runner, "inspect-cohort", "beta-testers")
    assert result.exit_code == 0


def test_inspect_cohort_shows_members(runner):
    invoke(runner, "create-cohort", "beta-testers")
    invoke(runner, "add-to-cohort", "beta-testers", "alice")
    result = invoke(runner, "inspect-cohort", "beta-testers")
    assert "alice" in result.output


# ── Full flag lifecycle via CLI ────────────────────────────────


def test_full_lifecycle_create_enable_disable_delete(runner, redis_client):
    invoke(runner, "create", "dark_mode", "--rollout", "100")
    invoke(runner, "enable", "dark_mode")

    # cache_ttl=0 so every call reads fresh from Redis
    flags = FeatureFlags(redis_client, env=E2E_ENV, cache_ttl=0)
    assert flags.is_enabled("dark_mode", user_id="alice") is True

    invoke(runner, "disable", "dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is False

    invoke(runner, "delete", "dark_mode", "--yes")
    assert flags.is_enabled("dark_mode", user_id="alice") is False
    assert flags.list_flags() == []


def test_rollout_progression_via_cli(runner, redis_client):
    invoke(runner, "create", "dark_mode")
    invoke(runner, "enable", "dark_mode")
    invoke(runner, "set-rollout", "dark_mode", "0")

    # cache_ttl=0 so every call reads fresh from Redis
    flags = FeatureFlags(redis_client, env=E2E_ENV, cache_ttl=0)
    assert flags.is_enabled("dark_mode", user_id="alice") is False

    invoke(runner, "set-rollout", "dark_mode", "100")
    assert flags.is_enabled("dark_mode", user_id="alice") is True
