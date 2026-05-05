import pytest
import fakeredis
from unittest.mock import patch
from typer.testing import CliRunner

from redis_flags.main import app
from redis_feature_flags import FeatureFlags

runner = CliRunner()


def make_redis_with_flag(flag_name="dark_mode"):
    fake = fakeredis.FakeRedis()
    flags = FeatureFlags(fake, env="test")
    flags.create(flag_name)
    return fake


def invoke(fake, args):
    with patch("redis_flags.commands.user.get_env", return_value="test"):
        with patch("redis_flags.commands.user.get_redis_url", return_value="redis://localhost:6379"):
            with patch("redis_flags.commands.user.get_client", return_value=fake):
                return runner.invoke(app, args)


# ── add-user ───────────────────────────────────────────────────


def test_add_user_success():
    """
    Given: flag dark_mode exists. Alice is not in allowlist.
    After: redis-flags add-user dark_mode alice called.
    Expected: exit code 0. Success message contains alice and dark_mode.
    """
    fake = make_redis_with_flag("dark_mode")
    result = invoke(fake, ["add-user", "dark_mode", "alice"])
    assert result.exit_code == 0
    assert "alice" in result.output
    assert "dark_mode" in result.output


def test_add_user_nonexistent_flag():
    """
    Given: flag nonexistent does not exist.
    After: redis-flags add-user nonexistent alice called.
    Expected: exit code 1. Error message shown.
    """
    fake = fakeredis.FakeRedis()
    result = invoke(fake, ["add-user", "nonexistent", "alice"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_add_multiple_users():
    """
    Given: flag dark_mode exists.
    After: alice and bob both added via add-user.
    Expected: both calls exit with code 0.
    """
    fake = make_redis_with_flag("dark_mode")
    result1 = invoke(fake, ["add-user", "dark_mode", "alice"])
    result2 = invoke(fake, ["add-user", "dark_mode", "bob"])
    assert result1.exit_code == 0
    assert result2.exit_code == 0


# ── remove-user ────────────────────────────────────────────────


def test_remove_user_success():
    """
    Given: alice is in the dark_mode allowlist.
    After: redis-flags remove-user dark_mode alice called.
    Expected: exit code 0. Success message contains alice and dark_mode.
    """
    fake = make_redis_with_flag("dark_mode")
    flags = FeatureFlags(fake, env="test")
    flags.add_user("dark_mode", "alice")
    result = invoke(fake, ["remove-user", "dark_mode", "alice"])
    assert result.exit_code == 0
    assert "alice" in result.output
    assert "dark_mode" in result.output


def test_remove_user_not_in_allowlist():
    """
    Given: alice is NOT in the dark_mode allowlist.
    After: redis-flags remove-user dark_mode alice called.
    Expected: exit code 0. Safe to remove non-existent user — no error.
    """
    fake = make_redis_with_flag("dark_mode")
    result = invoke(fake, ["remove-user", "dark_mode", "alice"])
    assert result.exit_code == 0