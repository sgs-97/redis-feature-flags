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
    """
    Given: FlagNotFoundError raised with flag name dark_mode.
    Expected: error message contains the flag name and a hint
              telling the developer how to create it.
    """
    e = FlagNotFoundError("dark_mode")
    assert "dark_mode" in str(e)
    assert "create" in str(e).lower()


def test_cohort_not_found_message():
    """
    Given: CohortNotFoundError raised with cohort name beta-testers.
    Expected: error message contains the cohort name.
    """
    e = CohortNotFoundError("beta-testers")
    assert "beta-testers" in str(e)


def test_invalid_rollout_message():
    """
    Given: InvalidRolloutError raised with value 150.
    Expected: error message contains 150 — the invalid value supplied.
              Rollout must be between 0 and 100.
    """
    e = InvalidRolloutError(150)
    assert "150" in str(e)


def test_schema_version_message():
    """
    Given: SchemaVersionError raised with expected=1 and found=2.
    Expected: error message contains both version numbers so the
              developer knows which version the SDK supports and
              which version Redis has.
    """
    e = SchemaVersionError("1", "2")
    assert "1" in str(e)
    assert "2" in str(e)


def test_all_inherit_from_base():
    """
    Given: all custom exception classes.
    Expected: every exception inherits from RedisFlagError.
              Allows callers to catch all library errors with
              a single except RedisFlagError block.
    """
    assert issubclass(FlagNotFoundError, RedisFlagError)
    assert issubclass(CohortNotFoundError, RedisFlagError)
    assert issubclass(InvalidRolloutError, RedisFlagError)
    assert issubclass(RedisConnectionError, RedisFlagError)
    assert issubclass(SchemaVersionError, RedisFlagError)


def test_base_inherits_from_exception():
    """
    Given: RedisFlagError base class.
    Expected: inherits from Python's built-in Exception.
              Ensures library errors behave like standard Python exceptions.
    """
    assert issubclass(RedisFlagError, Exception)