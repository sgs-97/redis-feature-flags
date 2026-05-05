import pytest
import fakeredis

from redis_feature_flags import FeatureFlags
from redis_feature_flags.exceptions import FlagNotFoundError, InvalidRolloutError


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis()


@pytest.fixture
def flags(redis_client):
    return FeatureFlags(redis_client, env="test")


def test_create_and_is_enabled_false_by_default(flags):
    """
    Given: flag created with no arguments.
    Expected: is_enabled() returns False — flags are disabled by default on creation.
    """
    flags.create("dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_create_and_enable(flags):
    """
    Given: flag created, enabled, and rollout set to 100.
    Expected: is_enabled() returns True — flag is on for everyone.
    """
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.set_rollout("dark_mode", 100)
    assert flags.is_enabled("dark_mode", user_id="alice") is True


def test_disable_flag(flags):
    """
    Given: flag enabled with rollout=100 then disabled.
    Expected: is_enabled() returns False — kill switch turns off the flag instantly.
    """
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.set_rollout("dark_mode", 100)
    flags.disable("dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_set_rollout(flags):
    """
    Given: flag enabled with rollout set to 100.
    Expected: is_enabled() returns True — 100% rollout means everyone gets the flag.
    """
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.set_rollout("dark_mode", 100)
    assert flags.is_enabled("dark_mode", user_id="alice") is True


def test_invalid_rollout_raises(flags):
    """
    Given: create() called with rollout=101.
    Expected: InvalidRolloutError raised — rollout must be between 0 and 100.
    """
    with pytest.raises(InvalidRolloutError):
        flags.create("dark_mode", rollout=101)


def test_enable_nonexistent_raises(flags):
    """
    Given: enable() called on a flag that does not exist.
    Expected: FlagNotFoundError raised — cannot enable a flag that was never created.
    """
    with pytest.raises(FlagNotFoundError):
        flags.enable("nonexistent")


def test_delete_flag(flags):
    """
    Given: flag created then deleted.
    Expected: is_enabled() returns False — flag is gone, default value returned.
    """
    flags.create("dark_mode")
    flags.delete("dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_list_flags(flags):
    """
    Given: two flags created — dark_mode and new_checkout.
    Expected: list_flags() returns both names.
              Uses the flags index Set — no KEYS * scan needed.
    """
    flags.create("dark_mode")
    flags.create("new_checkout")
    result = flags.list_flags()
    assert "dark_mode" in result
    assert "new_checkout" in result


def test_add_user_targeting(flags):
    """
    Given: flag enabled. Alice added to user allowlist. Bob is not.
    Expected: is_enabled() returns True for alice, False for bob.
              User allowlist overrides rollout percentage.
    """
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.add_user("dark_mode", "alice")
    assert flags.is_enabled("dark_mode", user_id="alice") is True
    assert flags.is_enabled("dark_mode", user_id="bob") is False


def test_remove_user_targeting(flags):
    """
    Given: alice added to allowlist then removed.
    Expected: is_enabled() returns False for alice — no longer in allowlist
              and rollout is 0.
    """
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.add_user("dark_mode", "alice")
    flags.remove_user("dark_mode", "alice")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_cohort_targeting(flags):
    """
    Given: flag enabled. Alice added to beta-testers cohort.
           beta-testers cohort added to flag. Bob is not in any cohort.
    Expected: is_enabled() returns True for alice, False for bob.
    """
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_cohort_to_flag("dark_mode", "beta-testers")
    assert flags.is_enabled("dark_mode", user_id="alice") is True
    assert flags.is_enabled("dark_mode", user_id="bob") is False


def test_get_flag(flags):
    """
    Given: flag created with rollout=10 and created_by=alice.
    Expected: get() returns a dict with the correct field values
              exactly as stored in Redis.
    """
    flags.create("dark_mode", rollout=10, created_by="alice")
    data = flags.get("dark_mode")
    assert data["rollout"] == "10"
    assert data["created_by"] == "alice"
    assert data["enabled"] == "0"


def test_missing_flag_returns_default(flags):
    """
    Given: flag that was never created.
    Expected: is_enabled() returns False by default.
              Returns True when default=True is explicitly passed.
    """
    assert flags.is_enabled("nonexistent", user_id="alice") is False
    assert flags.is_enabled("nonexistent", user_id="alice", default=True) is True


def test_remove_cohort_from_flag(flags):
    """
    Given: beta-testers cohort added to flag then removed.
    Expected: is_enabled() returns False — cohort no longer grants access.
    """
    flags.create("dark_mode")
    flags.create_cohort("beta-testers")
    flags.add_cohort_to_flag("dark_mode", "beta-testers")
    flags.remove_cohort_from_flag("dark_mode", "beta-testers")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_remove_from_cohort(flags):
    """
    Given: alice added to beta-testers cohort then removed.
    Expected: no error raised — remove_from_cohort() completes successfully.
    """
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.remove_from_cohort("beta-testers", "alice")


def test_set_rollout_invalid_raises(flags):
    """
    Given: set_rollout() called with value 150.
    Expected: InvalidRolloutError raised — rollout must be between 0 and 100.
    """
    flags.create("dark_mode")
    with pytest.raises(InvalidRolloutError):
        flags.set_rollout("dark_mode", 150)