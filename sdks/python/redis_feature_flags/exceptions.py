from __future__ import annotations


class RedisFlagError(Exception):
    """
    Base exception for all redis-feature-flags errors.

    Catch this to handle any error from the library:

        try:
            flags.enable("dark_mode")
        except RedisFlagError as e:
            print(f"Flag error: {e}")
    """
    pass


class FlagNotFoundError(RedisFlagError):
    """
    Raised when an operation is attempted on a flag that does not exist.

    Common causes:
        - Typo in flag name
        - Flag was deleted
        - Flag was never created

    Example:
        flags.enable("dark_mode")
        # raises FlagNotFoundError if dark_mode was never created

    Attributes:
        flag_name: The name of the flag that was not found.
    """

    def __init__(self, flag_name: str):
        self.flag_name = flag_name
        super().__init__(
            f"Flag '{flag_name}' not found.\n"
            f"Create it with: flags.create('{flag_name}')"
        )


class CohortNotFoundError(RedisFlagError):
    """
    Raised when an operation is attempted on a cohort that does not exist.

    Common causes:
        - Typo in cohort name
        - Cohort was deleted
        - Cohort was never created

    Example:
        flags.add_cohort_to_flag("dark_mode", "beta-testers")
        # raises CohortNotFoundError if beta-testers was never created

    Attributes:
        cohort_name: The name of the cohort that was not found.
    """

    def __init__(self, cohort_name: str):
        self.cohort_name = cohort_name
        super().__init__(
            f"Cohort '{cohort_name}' not found.\n"
            f"Create it with: flags.create_cohort('{cohort_name}')"
        )


class InvalidRolloutError(RedisFlagError):
    """
    Raised when a rollout percentage outside the range 0-100 is provided.

    Rollout must be an integer between 0 and 100 inclusive:
        0   = nobody gets the feature
        50  = 50% of users get the feature
        100 = everyone gets the feature

    Example:
        flags.create("dark_mode", rollout=150)
        # raises InvalidRolloutError — 150 is not a valid percentage
    """

    def __init__(self, value: int):
        super().__init__(
            f"Rollout must be between 0 and 100. Got: {value}"
        )


class RedisConnectionError(RedisFlagError):
    """
    Raised when Redis is unreachable and no cached data is available.

    This error only occurs when:
        1. Redis is down or unreachable, AND
        2. The local cache has no stale data to fall back on

    If the local cache has stale data — even expired — it will be served
    silently without raising this error. This error is the last resort
    when there is truly nothing to return.

    To avoid this error in production:
        - Configure Redis persistence: appendonly yes
        - Use a Redis instance with high availability
        - Pre-warm the cache on startup with flags.preload()
    """
    pass


class SchemaVersionError(RedisFlagError):
    """
    Raised when the Redis schema version is newer than this SDK supports.

    This happens when:
        - A newer version of redis-feature-flags wrote flags to Redis
        - An older SDK version tries to read those flags
        - The schema has breaking changes the old SDK does not understand

    Resolution:
        Upgrade redis-feature-flags to the latest version:
            pip install --upgrade redis-feature-flags

    Attributes:
        expected: The schema version this SDK supports.
        found:    The schema version found in Redis.

    Example:
        # SDK supports schema v1
        # Redis has schema v2 written by a newer SDK
        # raises SchemaVersionError("1", "2")
    """

    def __init__(self, expected: str, found: str):
        super().__init__(
            f"Schema version mismatch. "
            f"SDK supports version {expected}, "
            f"Redis has version {found}. "
            f"Please upgrade redis-feature-flags."
        )