import pytest
import fakeredis
from unittest.mock import patch
from typer.testing import CliRunner

from redis_flags.main import app
from redis_feature_flags import FeatureFlags

runner = CliRunner()


def make_redis():
    return fakeredis.FakeRedis()


def make_redis_with_cohort(cohort_name="beta-testers"):
    fake = fakeredis.FakeRedis()
    flags = FeatureFlags(fake, env="test")
    flags.create_cohort(cohort_name)
    return fake


def invoke(fake, args):
    with patch("redis_flags.commands.cohort.get_env", return_value="test"):
        with patch("redis_flags.commands.cohort.get_redis_url", return_value="redis://localhost:6379"):
            with patch("redis_flags.commands.cohort.get_client", return_value=fake):
                return runner.invoke(app, args)


# ── create-cohort ──────────────────────────────────────────────


def test_create_cohort_success():
    """
    Given: cohort beta-testers does not exist.
    After: redis-flags create-cohort beta-testers called.
    Expected: exit code 0. Success message contains cohort name.
    """
    fake = make_redis()
    result = invoke(fake, ["create-cohort", "beta-testers"])
    assert result.exit_code == 0
    assert "beta-testers" in result.output


# ── delete-cohort ──────────────────────────────────────────────


def test_delete_cohort_with_confirmation():
    """
    Given: cohort beta-testers exists.
    After: redis-flags delete-cohort beta-testers --yes called.
    Expected: exit code 0. Success message contains cohort name.
    """
    fake = make_redis_with_cohort("beta-testers")
    result = invoke(fake, ["delete-cohort", "beta-testers", "--yes"])
    assert result.exit_code == 0
    assert "beta-testers" in result.output


def test_delete_cohort_aborted_without_confirmation():
    """
    Given: cohort beta-testers exists.
    After: redis-flags delete-cohort beta-testers called — user types N.
    Expected: exit code 1. Operation aborted.
    """
    fake = make_redis_with_cohort("beta-testers")
    result = invoke(fake, ["delete-cohort", "beta-testers"])
    # runner sends empty input — defaults to N at confirmation prompt
    assert result.exit_code != 0


# ── add-to-cohort ──────────────────────────────────────────────


def test_add_to_cohort_success():
    """
    Given: cohort beta-testers exists. Alice is not a member.
    After: redis-flags add-to-cohort beta-testers alice called.
    Expected: exit code 0. Success message contains alice and beta-testers.
    """
    fake = make_redis_with_cohort("beta-testers")
    result = invoke(fake, ["add-to-cohort", "beta-testers", "alice"])
    assert result.exit_code == 0
    assert "alice" in result.output
    assert "beta-testers" in result.output


# ── remove-from-cohort ─────────────────────────────────────────


def test_remove_from_cohort_success():
    """
    Given: alice is a member of beta-testers cohort.
    After: redis-flags remove-from-cohort beta-testers alice called.
    Expected: exit code 0. Success message contains alice and beta-testers.
    """
    fake = make_redis_with_cohort("beta-testers")
    flags = FeatureFlags(fake, env="test")
    flags.add_to_cohort("beta-testers", "alice")
    result = invoke(fake, ["remove-from-cohort", "beta-testers", "alice"])
    assert result.exit_code == 0
    assert "alice" in result.output
    assert "beta-testers" in result.output


def test_remove_from_cohort_not_a_member():
    """
    Given: alice is NOT a member of beta-testers cohort.
    After: redis-flags remove-from-cohort beta-testers alice called.
    Expected: exit code 0. Safe to remove non-member — no error.
    """
    fake = make_redis_with_cohort("beta-testers")
    result = invoke(fake, ["remove-from-cohort", "beta-testers", "alice"])
    assert result.exit_code == 0


# ── list-cohorts ───────────────────────────────────────────────


def test_list_cohorts_shows_existing():
    """
    Given: cohort beta-testers exists.
    After: redis-flags list-cohorts called.
    Expected: exit code 0. beta-testers appears in output.
    """
    fake = make_redis_with_cohort("beta-testers")
    result = invoke(fake, ["list-cohorts"])
    assert result.exit_code == 0
    assert "beta-testers" in result.output


def test_list_cohorts_empty():
    """
    Given: no cohorts exist in Redis.
    After: redis-flags list-cohorts called.
    Expected: exit code 0. No cohorts found message shown.
    """
    fake = make_redis()
    result = invoke(fake, ["list-cohorts"])
    assert result.exit_code == 0
    assert "No cohorts found" in result.output


def test_list_cohorts_shows_multiple():
    """
    Given: beta-testers and premium-users cohorts exist.
    After: redis-flags list-cohorts called.
    Expected: exit code 0. Both cohort names appear in output.
    """
    fake = make_redis()
    flags = FeatureFlags(fake, env="test")
    flags.create_cohort("beta-testers")
    flags.create_cohort("premium-users")
    result = invoke(fake, ["list-cohorts"])
    assert result.exit_code == 0
    assert "beta-testers" in result.output
    assert "premium-users" in result.output


# ── inspect-cohort ─────────────────────────────────────────────


def test_inspect_cohort_shows_members():
    """
    Given: alice is a member of beta-testers cohort.
    After: redis-flags inspect-cohort beta-testers called.
    Expected: exit code 0. alice appears in output panel.
    """
    fake = make_redis_with_cohort("beta-testers")
    flags = FeatureFlags(fake, env="test")
    flags.add_to_cohort("beta-testers", "alice")
    result = invoke(fake, ["inspect-cohort", "beta-testers"])
    assert result.exit_code == 0
    assert "alice" in result.output


def test_inspect_cohort_empty():
    """
    Given: cohort beta-testers exists but has no members.
    After: redis-flags inspect-cohort beta-testers called.
    Expected: exit code 0. no members shown in output.
    """
    fake = make_redis_with_cohort("beta-testers")
    result = invoke(fake, ["inspect-cohort", "beta-testers"])
    assert result.exit_code == 0
    assert "no members" in result.output

def test_list_cohorts_empty_message():
    """
    Given: no cohorts exist.
    After: redis-flags list-cohorts called.
    Expected: output contains No cohorts found.
    """
    fake = make_redis()
    result = invoke(fake, ["list-cohorts"])
    assert result.exit_code == 0
    assert "No cohorts found" in result.output