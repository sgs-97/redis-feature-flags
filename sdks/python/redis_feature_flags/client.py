from __future__ import annotations

from typing import Dict, List, Optional, Any

import redis

from .cache import LocalCache
from .cohorts import CohortManager
from .evaluator import Evaluator
from .exceptions import FlagNotFoundError, InvalidRolloutError
from .schema import SchemaKeys
from .utils import now_unix


class FeatureFlags:
    """
    Main entry point for redis-feature-flags.

    Usage:
        import redis
        from redis_feature_flags import FeatureFlags

        r = redis.Redis()
        flags = FeatureFlags(r)

        flags.create("dark_mode", rollout=10)
        flags.is_enabled("dark_mode", user_id="alice")
    """

    SCHEMA_VERSION = "1"

    def __init__(
        self,
        redis_client: redis.Redis,
        env: str = "prod",
        cache_ttl: int = 30,
    ):
        self._redis = redis_client
        self._schema = SchemaKeys(env=env)
        self._cache = LocalCache(ttl_seconds=cache_ttl)
        self._evaluator = Evaluator(redis_client, self._schema, self._cache)
        self._cohorts = CohortManager(redis_client, self._schema)

    # ── Core evaluation ────────────────────────────────────────

    def is_enabled(
        self,
        flag_name: str,
        user_id: str,
        default: bool = False,
    ) -> bool:
        return self._evaluator.is_enabled(flag_name, user_id, default)

    # ── Flag management ────────────────────────────────────────

    def create(
        self,
        flag_name: str,
        rollout: int = 0,
        created_by: str = "unknown",
    ) -> None:
        if not 0 <= rollout <= 100:
            raise InvalidRolloutError(rollout)
        ts = str(now_unix())
        self._redis.hset(
            self._schema.flag(flag_name),
            mapping={
                "enabled":      "0",
                "rollout":      str(rollout),
                "expires_at":   "0",
                "created_at":   ts,
                "updated_at":   ts,
                "created_by":   created_by,
                "updated_by":   created_by,
                "flag_version": "1",
            },
        )
        self._redis.sadd(self._schema.flags_index(), flag_name)

    def enable(self, flag_name: str, updated_by: str = "unknown") -> None:
        self._assert_exists(flag_name)
        self._redis.hset(
            self._schema.flag(flag_name),
            mapping={
                "enabled":    "1",
                "updated_at": str(now_unix()),
                "updated_by": updated_by,
            },
        )
        self._cache.delete(self._schema.flag(flag_name))

    def disable(self, flag_name: str, updated_by: str = "unknown") -> None:
        self._assert_exists(flag_name)
        self._redis.hset(
            self._schema.flag(flag_name),
            mapping={
                "enabled":    "0",
                "updated_at": str(now_unix()),
                "updated_by": updated_by,
            },
        )
        self._cache.delete(self._schema.flag(flag_name))

    def set_rollout(
        self,
        flag_name: str,
        percent: int,
        updated_by: str = "unknown",
    ) -> None:
        if not 0 <= percent <= 100:
            raise InvalidRolloutError(percent)
        self._assert_exists(flag_name)
        self._redis.hset(
            self._schema.flag(flag_name),
            mapping={
                "rollout":    str(percent),
                "updated_at": str(now_unix()),
                "updated_by": updated_by,
            },
        )
        self._cache.delete(self._schema.flag(flag_name))

    def delete(self, flag_name: str) -> None:
        self._redis.delete(self._schema.flag(flag_name))
        self._redis.delete(self._schema.flag_users(flag_name))
        self._redis.delete(self._schema.flag_cohorts(flag_name))
        self._redis.delete(self._schema.flag_history(flag_name))
        self._redis.srem(self._schema.flags_index(), flag_name)
        self._cache.delete(self._schema.flag(flag_name))

    def list_flags(self) -> List[str]:
        flags = self._redis.smembers(self._schema.flags_index())
        return sorted([f.decode() for f in flags])

    def get(self, flag_name: str) -> Dict[str, Any]:
        self._assert_exists(flag_name)
        data = self._redis.hgetall(self._schema.flag(flag_name))
        return {k.decode(): v.decode() for k, v in data.items()}

    # ── User targeting ─────────────────────────────────────────

    def add_user(self, flag_name: str, user_id: str) -> None:
        self._assert_exists(flag_name)
        self._redis.sadd(self._schema.flag_users(flag_name), user_id)

    def remove_user(self, flag_name: str, user_id: str) -> None:
        self._redis.srem(self._schema.flag_users(flag_name), user_id)

    # ── Cohort targeting ───────────────────────────────────────

    def create_cohort(self, cohort_name: str) -> None:
        self._cohorts.create(cohort_name)

    def add_to_cohort(self, cohort_name: str, user_id: str) -> None:
        self._cohorts.add_user(cohort_name, user_id)

    def remove_from_cohort(self, cohort_name: str, user_id: str) -> None:
        self._cohorts.remove_user(cohort_name, user_id)

    def add_cohort_to_flag(self, flag_name: str, cohort_name: str) -> None:
        self._assert_exists(flag_name)
        self._redis.sadd(self._schema.flag_cohorts(flag_name), cohort_name)

    def remove_cohort_from_flag(
        self, flag_name: str, cohort_name: str
    ) -> None:
        self._redis.srem(self._schema.flag_cohorts(flag_name), cohort_name)

    # ── Private helpers ────────────────────────────────────────

    def _assert_exists(self, flag_name: str) -> None:
        if not self._redis.exists(self._schema.flag(flag_name)):
            raise FlagNotFoundError(flag_name)