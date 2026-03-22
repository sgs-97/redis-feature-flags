from __future__ import annotations

import redis

from .exceptions import CohortNotFoundError
from .schema import SchemaKeys


class CohortManager:
    def __init__(
        self,
        redis_client: redis.Redis,
        schema: SchemaKeys,
    ):
        self._redis = redis_client
        self._schema = schema

    def create(self, cohort_name: str) -> None:
        self._redis.sadd(self._schema.cohorts_index(), cohort_name)

    def delete(self, cohort_name: str) -> None:
        self._redis.delete(self._schema.cohort(cohort_name))
        self._redis.srem(self._schema.cohorts_index(), cohort_name)

    def add_user(self, cohort_name: str, user_id: str) -> None:
        pipe = self._redis.pipeline()
        pipe.sadd(self._schema.cohort(cohort_name), user_id)
        pipe.sadd(self._schema.user_cohorts(user_id), cohort_name)
        pipe.execute()

    def remove_user(self, cohort_name: str, user_id: str) -> None:
        pipe = self._redis.pipeline()
        pipe.srem(self._schema.cohort(cohort_name), user_id)
        pipe.srem(self._schema.user_cohorts(user_id), cohort_name)
        pipe.execute()

    def get_members(self, cohort_name: str) -> set:
        members = self._redis.smembers(self._schema.cohort(cohort_name))
        return {m.decode() for m in members}

    def list_cohorts(self) -> list:
        cohorts = self._redis.smembers(self._schema.cohorts_index())
        return [c.decode() for c in cohorts]

    def exists(self, cohort_name: str) -> bool:
        return bool(
            self._redis.sismember(
                self._schema.cohorts_index(), cohort_name
            )
        )
