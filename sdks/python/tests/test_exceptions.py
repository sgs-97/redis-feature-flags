import pytest
from redis_feature_flags.exceptions import (
    RedisFlagError,
    FlagNotFoundError,
    CohortNotFoundError,
    InvalidRolloutError,
    SchemaVersionError,
    RedisConnectionError,
)


def test_flag_not_found_message():
    e = FlagNotFoundError("dark_mode")
    assert "dark_mode" in str(e)
    assert "create" in str(e).lower()


def test_cohort_not_found_message():
    e = CohortNotFoundError("beta-testers")
    assert "beta-testers" in str(e)


def test_invalid_rollout_message():
    e = InvalidRolloutError(150)
    assert "150" in str(e)


def test_schema_version_message():
    e = SchemaVersionError("1", "2")
    assert "1" in str(e)
    assert "2" in str(e)


def test_all_inherit_from_base():
    assert issubclass(FlagNotFoundError, RedisFlagError)
    assert issubclass(CohortNotFoundError, RedisFlagError)
    assert issubclass(InvalidRolloutError, RedisFlagError)
    assert issubclass(RedisConnectionError, RedisFlagError)
    assert issubclass(SchemaVersionError, RedisFlagError)


def test_base_inherits_from_exception():
    assert issubclass(RedisFlagError, Exception)