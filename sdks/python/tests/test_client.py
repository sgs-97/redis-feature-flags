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
    flags.create("dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_create_and_enable(flags):
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.set_rollout("dark_mode", 100)
    assert flags.is_enabled("dark_mode", user_id="alice") is True


def test_disable_flag(flags):
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.set_rollout("dark_mode", 100)
    flags.disable("dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_set_rollout(flags):
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.set_rollout("dark_mode", 100)
    assert flags.is_enabled("dark_mode", user_id="alice") is True


def test_invalid_rollout_raises(flags):
    with pytest.raises(InvalidRolloutError):
        flags.create("dark_mode", rollout=101)


def test_enable_nonexistent_raises(flags):
    with pytest.raises(FlagNotFoundError):
        flags.enable("nonexistent")


def test_delete_flag(flags):
    flags.create("dark_mode")
    flags.delete("dark_mode")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_list_flags(flags):
    flags.create("dark_mode")
    flags.create("new_checkout")
    result = flags.list_flags()
    assert "dark_mode" in result
    assert "new_checkout" in result


def test_add_user_targeting(flags):
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.add_user("dark_mode", "alice")
    assert flags.is_enabled("dark_mode", user_id="alice") is True
    assert flags.is_enabled("dark_mode", user_id="bob") is False


def test_remove_user_targeting(flags):
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.add_user("dark_mode", "alice")
    flags.remove_user("dark_mode", "alice")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_cohort_targeting(flags):
    flags.create("dark_mode")
    flags.enable("dark_mode")
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.add_cohort_to_flag("dark_mode", "beta-testers")
    assert flags.is_enabled("dark_mode", user_id="alice") is True
    assert flags.is_enabled("dark_mode", user_id="bob") is False


def test_get_flag(flags):
    flags.create("dark_mode", rollout=10, created_by="alice")
    data = flags.get("dark_mode")
    assert data["rollout"] == "10"
    assert data["created_by"] == "alice"
    assert data["enabled"] == "0"


def test_missing_flag_returns_default(flags):
    assert flags.is_enabled("nonexistent", user_id="alice") is False
    assert flags.is_enabled("nonexistent", user_id="alice", default=True) is True

def test_remove_cohort_from_flag(flags):
    flags.create("dark_mode")
    flags.create_cohort("beta-testers")
    flags.add_cohort_to_flag("dark_mode", "beta-testers")
    flags.remove_cohort_from_flag("dark_mode", "beta-testers")
    assert flags.is_enabled("dark_mode", user_id="alice") is False


def test_remove_from_cohort(flags):
    flags.create_cohort("beta-testers")
    flags.add_to_cohort("beta-testers", "alice")
    flags.remove_from_cohort("beta-testers", "alice")


def test_set_rollout_invalid_raises(flags):
    flags.create("dark_mode")
    with pytest.raises(InvalidRolloutError):
        flags.set_rollout("dark_mode", 150)