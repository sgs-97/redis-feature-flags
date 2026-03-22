class RedisFlagError(Exception):
    """Base exception for redis-feature-flags."""
    pass


class FlagNotFoundError(RedisFlagError):
    def __init__(self, flag_name: str):
        self.flag_name = flag_name
        super().__init__(
            f"Flag '{flag_name}' not found.\n"
            f"Create it with: flags.create('{flag_name}')"
        )


class CohortNotFoundError(RedisFlagError):
    def __init__(self, cohort_name: str):
        self.cohort_name = cohort_name
        super().__init__(
            f"Cohort '{cohort_name}' not found.\n"
            f"Create it with: flags.create_cohort('{cohort_name}')"
        )


class InvalidRolloutError(RedisFlagError):
    def __init__(self, value: int):
        super().__init__(
            f"Rollout must be between 0 and 100. Got: {value}"
        )


class RedisConnectionError(RedisFlagError):
    """Raised when Redis is unreachable and no cache is available."""
    pass


class SchemaVersionError(RedisFlagError):
    def __init__(self, expected: str, found: str):
        super().__init__(
            f"Schema version mismatch. "
            f"SDK supports version {expected}, "
            f"Redis has version {found}. "
            f"Please upgrade redis-feature-flags."
        )