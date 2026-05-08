import pytest
import fakeredis
from unittest.mock import patch
from typer.testing import CliRunner

from redis_flags.main import app
from redis_feature_flags import FeatureFlags

runner = CliRunner()


def make_redis():
    """Create a clean fakeredis instance."""
    return fakeredis.FakeRedis()


def make_redis_with_flag(flag_name="dark_mode", rollout=0, enabled=False):
    """Create fakeredis with a pre-existing flag."""
    fake = fakeredis.FakeRedis()
    flags = FeatureFlags(fake, env="test")
    flags.create(flag_name, rollout=rollout)
    if enabled:
        flags.enable(flag_name)
    return fake


def invoke(fake, args):
    with patch("redis_flags.commands.flag.get_env", return_value="test"):
        with patch("redis_flags.commands.flag.get_redis_url", return_value="redis://localhost:6379"):
            with patch("redis_flags.commands.flag.get_client", return_value=fake):
                return runner.invoke(app, args)

# ── create ─────────────────────────────────────────────────────


def test_create_flag_success():
    """
    Given: flag dark_mode does not exist.
    After: redis-flags create dark_mode called.
    Expected: exit code 0. Success message contains flag name.
    """
    fake = make_redis()
    result = invoke(fake, ["create", "dark_mode"])
    assert result.exit_code == 0
    assert "dark_mode" in result.output


def test_create_flag_with_rollout():
    """
    Given: redis-flags create dark_mode --rollout 50 called.
    Expected: exit code 0. Output contains rollout percentage.
    """
    fake = make_redis()
    result = invoke(fake, ["create", "dark_mode", "--rollout", "50"])
    assert result.exit_code == 0
    assert "50%" in result.output


def test_create_flag_invalid_rollout():
    """
    Given: redis-flags create dark_mode --rollout 150 called.
    Expected: exit code 1. Rollout 150 is invalid — must be 0-100.
    """
    fake = make_redis()
    result = invoke(fake, ["create", "dark_mode", "--rollout", "150"])
    assert result.exit_code == 1


def test_create_flag_with_created_by():
    """
    Given: redis-flags create dark_mode --created-by alice called.
    Expected: exit code 0. Flag created successfully.
    """
    fake = make_redis()
    result = invoke(fake, ["create", "dark_mode", "--created-by", "alice"])
    assert result.exit_code == 0
    assert "dark_mode" in result.output


# ── enable ─────────────────────────────────────────────────────


def test_enable_existing_flag():
    """
    Given: flag dark_mode exists and is disabled.
    After: redis-flags enable dark_mode called.
    Expected: exit code 0. Success message contains flag name.
    """
    fake = make_redis_with_flag("dark_mode")
    result = invoke(fake, ["enable", "dark_mode"])
    assert result.exit_code == 0
    assert "dark_mode" in result.output


def test_enable_nonexistent_flag():
    """
    Given: flag nonexistent does not exist.
    After: redis-flags enable nonexistent called.
    Expected: exit code 1. Error message shown.
    """
    fake = make_redis()
    result = invoke(fake, ["enable", "nonexistent"])
    assert result.exit_code == 1
    assert "Error" in result.output


# ── disable ────────────────────────────────────────────────────


def test_disable_existing_flag():
    """
    Given: flag dark_mode exists and is enabled.
    After: redis-flags disable dark_mode called.
    Expected: exit code 0. Success message contains flag name.
    """
    fake = make_redis_with_flag("dark_mode", enabled=True)
    result = invoke(fake, ["disable", "dark_mode"])
    assert result.exit_code == 0
    assert "dark_mode" in result.output


def test_disable_nonexistent_flag():
    """
    Given: flag nonexistent does not exist.
    After: redis-flags disable nonexistent called.
    Expected: exit code 1. Error message shown.
    """
    fake = make_redis()
    result = invoke(fake, ["disable", "nonexistent"])
    assert result.exit_code == 1
    assert "Error" in result.output


# ── set-rollout ────────────────────────────────────────────────


def test_set_rollout_success():
    """
    Given: flag dark_mode exists.
    After: redis-flags set-rollout dark_mode 50 called.
    Expected: exit code 0. Output contains 50%.
    """
    fake = make_redis_with_flag("dark_mode")
    result = invoke(fake, ["set-rollout", "dark_mode", "50"])
    assert result.exit_code == 0
    assert "50%" in result.output


def test_set_rollout_invalid():
    """
    Given: flag dark_mode exists.
    After: redis-flags set-rollout dark_mode 150 called.
    Expected: exit code 1. 150 is not a valid rollout percentage.
    """
    fake = make_redis_with_flag("dark_mode")
    result = invoke(fake, ["set-rollout", "dark_mode", "150"])
    assert result.exit_code == 1


def test_set_rollout_nonexistent_flag():
    """
    Given: flag nonexistent does not exist.
    After: redis-flags set-rollout nonexistent 50 called.
    Expected: exit code 1. Error message shown.
    """
    fake = make_redis()
    result = invoke(fake, ["set-rollout", "nonexistent", "50"])
    assert result.exit_code == 1


# ── delete ─────────────────────────────────────────────────────


def test_delete_flag_with_confirmation():
    """
    Given: flag dark_mode exists.
    After: redis-flags delete dark_mode --yes called.
    Expected: exit code 0. Success message contains flag name.
    """
    fake = make_redis_with_flag("dark_mode")
    result = invoke(fake, ["delete", "dark_mode", "--yes"])
    assert result.exit_code == 0
    assert "dark_mode" in result.output


def test_delete_flag_aborted_without_confirmation():
    """
    Given: flag dark_mode exists.
    After: redis-flags delete dark_mode called — user types N at prompt.
    Expected: exit code 1. Operation aborted — flag not deleted.
    """
    fake = make_redis_with_flag("dark_mode")
    result = invoke(fake, ["delete", "dark_mode"])
    assert result.exit_code != 0


def test_delete_nonexistent_flag():
    """
    Given: flag nonexistent does not exist.
    After: redis-flags delete nonexistent --yes called.
    Expected: exit code 0 — Redis DEL on missing key is a no-op, not an error.
    """
    fake = make_redis()
    result = invoke(fake, ["delete", "nonexistent", "--yes"])
    assert result.exit_code == 0


# ── list ───────────────────────────────────────────────────────


def test_list_shows_existing_flags():
    fake = make_redis_with_flag("dark_mode")
    result = invoke(fake, ["list"])
    print(result.output)
    print(result.exception)
    assert result.exit_code == 0
    assert "dark_mode" in result.output


def test_list_empty_when_no_flags():
    """
    Given: no flags exist in Redis.
    After: redis-flags list called.
    Expected: exit code 0. No flags found message shown.
    """
    fake = make_redis()
    result = invoke(fake, ["list"])
    assert result.exit_code == 0
    assert "No flags found" in result.output


def test_list_shows_multiple_flags():
    """
    Given: dark_mode and new_checkout flags exist.
    After: redis-flags list called.
    Expected: exit code 0. Both flag names appear in output.
    """
    fake = make_redis()
    flags = FeatureFlags(fake, env="test")
    flags.create("dark_mode")
    flags.create("new_checkout")
    result = invoke(fake, ["list"])
    assert result.exit_code == 0
    assert "dark_mode" in result.output
    assert "new_checkout" in result.output


# ── inspect ────────────────────────────────────────────────────


def test_inspect_existing_flag():
    """
    Given: flag dark_mode exists.
    After: redis-flags inspect dark_mode called.
    Expected: exit code 0. Flag name appears in output panel.
    """
    fake = make_redis_with_flag("dark_mode", rollout=10)
    result = invoke(fake, ["inspect", "dark_mode"])
    assert result.exit_code == 0
    assert "dark_mode" in result.output


def test_inspect_shows_enabled_status():
    """
    Given: flag dark_mode is enabled.
    After: redis-flags inspect dark_mode called.
    Expected: output contains 'yes' for enabled status.
    """
    fake = make_redis_with_flag("dark_mode", enabled=True)
    result = invoke(fake, ["inspect", "dark_mode"])
    assert result.exit_code == 0
    assert "yes" in result.output


def test_inspect_shows_disabled_status():
    """
    Given: flag dark_mode is disabled.
    After: redis-flags inspect dark_mode called.
    Expected: output contains 'no' for enabled status.
    """
    fake = make_redis_with_flag("dark_mode", enabled=False)
    result = invoke(fake, ["inspect", "dark_mode"])
    assert result.exit_code == 0
    assert "no" in result.output


def test_inspect_nonexistent_flag():
    """
    Given: flag nonexistent does not exist.
    After: redis-flags inspect nonexistent called.
    Expected: exit code 1. Error message shown.
    """
    fake = make_redis()
    result = invoke(fake, ["inspect", "nonexistent"])
    assert result.exit_code == 1
    assert "Error" in result.output

def test_list_shows_existing_flags():
    fake = make_redis_with_flag("dark_mode")
    
    # verify flag exists before invoking
    keys = fake.smembers("ff:test:flag:__index__")
    print("Before invoke — index:", keys)
    
    result = invoke(fake, ["list"])
    print("Output:", result.output)
    assert result.exit_code == 0
    assert "dark_mode" in result.output

def test_delete_nonexistent_flag_shows_error():
    """
    Given: flag nonexistent does not exist.
    After: redis-flags delete nonexistent --yes called.
    Expected: exit code 1 when FlagNotFoundError is raised.
    """
    fake = make_redis()
    # make delete raise FlagNotFoundError by making _assert_exists fail
    from unittest.mock import patch as p2
    from redis_feature_flags.exceptions import FlagNotFoundError
    with patch("redis_flags.commands.flag.get_env", return_value="test"):
        with patch("redis_flags.commands.flag.get_redis_url", return_value="redis://localhost:6379"):
            with patch("redis_flags.commands.flag.get_client", return_value=fake):
                with p2("redis_feature_flags.client.FeatureFlags.delete",
                        side_effect=FlagNotFoundError("nonexistent")):
                    result = runner.invoke(app, ["delete", "nonexistent", "--yes"])
    assert result.exit_code == 1
    assert "Error" in result.output

def test_inspect_flag_with_invalid_timestamp():
    """
    Given: flag exists with invalid expires_at value.
    Expected: inspect handles bad timestamp gracefully — no crash.
    """
    fake = fakeredis.FakeRedis()
    fake.hset("ff:test:flag:dark_mode", mapping={
        "enabled": "0", "rollout": "0",
        "expires_at": "invalid", "flag_version": "1",
        "created_at": "invalid", "updated_at": "invalid",
        "created_by": "test", "updated_by": "test"
    })
    fake.sadd("ff:test:flag:__index__", "dark_mode")
    result = invoke(fake, ["inspect", "dark_mode"])
    assert result.exit_code == 0

def test_history_command_shows_placeholder():
    """
    Given: redis-flags history dark_mode called.
    Expected: exit code 0. Shows v1.1 placeholder message.
    """
    fake = make_redis()
    result = invoke(fake, ["history", "dark_mode"])
    assert result.exit_code == 0
    assert "v1.1" in result.output


def test_rollback_command_shows_placeholder():
    """
    Given: redis-flags rollback dark_mode --version 1 called.
    Expected: exit code 0. Shows v1.1 placeholder message.
    """
    fake = make_redis()
    result = invoke(fake, ["rollback", "dark_mode", "--version", "1"])
    assert result.exit_code == 0
    assert "v1.1" in result.output